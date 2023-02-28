# -*- coding: utf-8 -*-
#####################################################################################################
#
# Copyright:
#   - 2022 T.Fischer <mail |at| sedi -DOT- one>
#   - 2023 T.Fischer <mail |at| sedi -DOT- one>
#
# License: GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
#####################################################################################################

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
from ansible.module_utils._text import to_native
from ansible_collections.sedi.openaudit.plugins.module_utils.common import OA_vars as oavars
from ansible_collections.sedi.openaudit.plugins.module_utils.common import OA_get as oaget
from ansible_collections.sedi.openaudit.plugins.module_utils.common import OA_misc as oamisc


class OA_device():

    def get_field(self, field, task_vars, tmp, margs, return_valid_fields=False):
        """
        fetch a specified field for a specific device fqdn
        returns the value of that field.
        if no matching field name could be found return None or all valid fields (if requested)
        """

        p_field = field.rpartition("system.")[-1]

        # first try to get value from host vars
        for hvk, hvv in task_vars.items():
            if p_field == hvk:
                return hvv

        # ... if not avail as hostvar fetch all device info
        try:
            get_ret = oaget.api(self, tmp=tmp, task_vars=task_vars, parsed_args=margs)
        except Exception as e:
            raise e

        # ... and try first the internal fields attached to the device
        for rd in get_ret['data']:
            # print(rd['attributes'])
            for dk, dv in rd['attributes'].items():
                if p_field == dk:
                    return dv

        # ... and as last try parse all custom fields attached to the device
        for a in get_ret['included']:
            if a['type'] == 'audit_log':
                continue
            for ik, iv in a['attributes'].items():
                if p_field == ik:
                    return iv

        # ... when there is no match, return None or valid fields
        if return_valid_fields:
            ret = OA_device.get_valid_fields(self, margs, task_vars, tmp)
            ret.update(failed=True)
            return ret
        else:
            return None

    def get_valid_fields(self, module_field_args, task_vars, tmp):
        """
        get all valid fields for a device
        returns a dict of valid field names
        """

        validfields = {}
        try:
            am_ret = oaget.api(self, tmp=tmp, task_vars=task_vars, parsed_args=module_field_args)
            validfields['Valid Open-AudIT fields'] = oamisc.replace_oa_prefix(self, data=am_ret['meta']['data_order'])
        except Exception as e:
            raise e

        vf_sorted = sorted(validfields.items(), key=lambda item: item[1])
        return dict(vf_sorted)

    def parse_device_data(self, data, fqdn):
        """
        parse given device data for a specific device fqdn
        returns all attached attributes of a device
        """
        ret = {}
        try:
            for a in data:
                if a['attributes']['system.fqdn'] == fqdn:
                    # print("found device id: " + str(a['attributes']['system.id']))
                    for i in a['attributes']:
                        ret[i] = a['attributes'][i]
                    return ret
            # this should never happen usually. but... if e.g. a host is defined in a static
            # hosts list but not in Open-AudIT we need to catch this here
            raise ValueError("Could not find matching device id for FQDN")
        except Exception as e:
            raise e

    def map_id(self, field, dfm, mf_ret):
        """
        return a translated field name based on its id
        return None if no mapping was found
        """
        for fm, fv in dfm.items():
            if fm == field:
                for f in mf_ret['data']:
                    # if we have a match for the field id set trans_k and go on
                    if fv is f['attributes']['fields.id']:
                        trans_k = f['attributes']['fields.name']
                        return trans_k
        return None

    def cmp_field_prop(self, fname, tname, fvalue, margs, did, server, tmp, task_vars):
        """
        compare a given field value with the API result
        returns true if it is identical and false if not
        will return "None" if no match found as well - which actually should not happen at all
        """

        # depending on if the requested field is a special attribute or a custom field
        # handle it accordingly
        if tname is not None:
            array = "data"
            margs['url'] = server + oavars.device_uri_path + '/' + did + '?format=json&properties=' + tname
        else:
            array = "included"
            # devices/20?format=json&include=field&properties=system.status
            margs['url'] = server + oavars.device_uri_path + '/' + did + '?format=json&include=field'

        # fetch in the right context
        ret = oaget.api(self, parsed_args=margs, task_vars=task_vars, tmp=tmp)

        # return true or false depending on if it the fetched value differs
        if tname is not None:
            for f in ret[array]:
                for i, v in f['attributes'].items():
                    if i == tname:
                        if fvalue == v:
                            # print("not changed: %s" % tname)
                            return True
                        else:
                            # print("changed: %s -> %s" % (tname, fvalue))
                            return False
        else:
            for f in ret[array]:
                if fname == f['attributes']['name']:
                    # print("found fname match")
                    if fvalue == f['attributes']['value']:
                        # print("not changed: %s" % fname)
                        return True
                    else:
                        # print("changed: %s -> %s" % (fname, fvalue))
                        return False

        return None

    def update(self, scheme_server, task_vars, module_args, tmp, device_data):
        """
        updates device properties/attributes
        returns full server response
        """
        # TODO: maybe a quick search for the fqdn in the whole lists of dicts first?
        try:
            api_content = oaget.api(self, tmp=tmp, task_vars=task_vars, parsed_args=module_args)
            parsed_device_data = OA_device.parse_device_data(self, data=api_content['data'], fqdn=device_data['fqdn'])
        except Exception as e:
            raise e

        device_id = str(parsed_device_data['system.id'])

        # curl .. -d 'data={"data":{"id":"161","type":"devices","attributes":{"org_id":"2"}}}'
        body_data = {}
        body_data['data'] = {}
        body_data['data']['id'] = device_id
        body_data['data']['type'] = "devices"
        body_data['data']['attributes'] = {}

        module_field_args = module_args
        module_field_args['method'] = "GET"

        # fetch all custom(!) fields and their ids
        module_field_args['url'] = scheme_server + oavars.fields_names_uri_path
        mf_ret = oaget.api(self, tmp=tmp, task_vars=task_vars, parsed_args=module_field_args)

        # load custom field <-> id mapping
        dictFieldMap = task_vars['dictFieldMap']

        # set change required var to default False (gets overwritten if needed)
        chgreq = False

        # initial value for key validation
        invalid_key = False

        # parse and update
        # k = key name set by user
        tDict = {}
        for kp in device_data['fields']:
            k = str(kp)
            trans_k = None
            prop_sk = None

            # check for internal id first
            if k.rpartition(oavars.oa_fields_prefix)[1]:
                trans_k = k.rpartition(oavars.oa_fields_prefix)[-1]
                prop_sk = trans_k
                # print(prop_sk)
            else:
                # parse through static translation items
                for sk, sv in oavars.singleDeviceT.items():
                    if k == sv:
                        # device properties have to use the format <collection>'.'<name> for GET
                        # but for POST/PATCH it has to be just the <name> so we need to trim them
                        # if needed first
                        trans_k = sk.rpartition('.')[-1] or sk
                        if sk is not trans_k:
                            prop_sk = sk
                        break

            # if the key does not match a static translation item loop through the
            # custom field mappings and map the real field name with its translation
            # user sets "abc", the field mapping says "abc" = 33, Open-AudIT maps id 33
            # to a field named "this is abc". the following makes it possible to use just
            # the custom field mapping "abc" instead of the long named "this is abc"
            # which we need in our POST/PATCH call though
            if trans_k is None:
                trans_k = OA_device.map_id(self, dfm=dictFieldMap, mf_ret=mf_ret, field=k)

            if trans_k is not None:
                # print("processing: %s" % trans_k)
                val_res = OA_device.cmp_field_prop(self, fname=trans_k, tname=prop_sk, did=device_id,
                                                   fvalue=device_data['fields'][k],
                                                   tmp=tmp, task_vars=task_vars,
                                                   server=scheme_server, margs=module_field_args)
                if val_res is None:
                    # no valid field found
                    invalid_key = k
                elif not val_res:
                    chgreq = True
                    body_data['data']['attributes'][trans_k] = device_data['fields'][k]
                    # print('Translated field ids and their values: %s' % str(body_data['data']['attributes']))
            else:
                # no valid field found
                # print(trans_k)
                invalid_key = k

        # invalid keys will fail and show valid ones
        if invalid_key is not False:
            module_field_args['url'] = scheme_server + oavars.device_uri_path + '/' + device_id + '?format=json&include=all'
            ret = OA_device.get_valid_fields(self, module_field_args, task_vars, tmp)
            return dict(failed=True, message=ret,
                        original_message=oavars.wrong_field_msg
                        % invalid_key)

        if chgreq:
            # finally if we have a diff value then in OA update it there
            try:
                module_args['method'] = "PATCH"
                module_args['url'] = scheme_server + oavars.device_uri_path + "/" + device_id
                module_args['body'] = "data=" + json.dumps(body_data)
                ret = oaget.api(self, tmp=tmp, task_vars=task_vars, parsed_args=module_args)
            except Exception as e:
                raise Exception("Problem occured while updating the following attributes:\n" + json.dumps(body_data) + "\n%s" % to_native(e))

            # add proper output
            module_return = {}
            module_return['Changed Open-AudIT fields'] = {}
            for mk, mv in body_data['data']['attributes'].items():
                module_return['Changed Open-AudIT fields'][mk] = "changed to >" + str(mv) + "<"
                module_return.update(module_return, changed=True)
        else:
            # set initial module return to skipped (gets overwritten if we change smth)
            module_return = dict(changed=False, message='All fields have their requested values set already')

        return module_return
