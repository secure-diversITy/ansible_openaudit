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

# required imports
from ansible_collections.sedi.openaudit.plugins.module_utils.common import OA_vars as oavars
from ansible_collections.sedi.openaudit.plugins.module_utils.common import OA_get as oaget
from ansible_collections.sedi.openaudit.plugins.module_utils.device import OA_device as oadev
from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail
from ansible.module_utils._text import to_native


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):

        result = super(ActionModule, self).run(tmp, task_vars)
        _args = self._task.args.copy()
        module_args = dict()

        scheme_server = _args['api_protocol'] + "://" + _args['api_server']

        # while it is recommended using the internal requests module I was not able to get it work so using uri module instead
        # from ansible.module_utils.urls import Request
        # r = Request(validate_certs=_args['validate_certs'], cookies=oalogin_ret.cookies)
        # moo = r.open('POST', scheme_server + oavars.logon_uri_path, data=dict(username=_args['username'],password=_args['password'])).read()
        # = Request(headers=dict(foo='bar'))
        # moo = url.open_url(scheme_server + oavars.logon_uri_path, validate_certs=_args['validate_certs'], cookies=oalogin_ret.cookies).read()
        # moo = r.open('POST', scheme_server + oavars.logon_uri_path, cookies=oalogin_ret.cookies).read()
        # moo = r.open('GET', scheme_server + oavars.locations_uri_path, cookies=oalogin_ret.cookies).read()
        # moo = r.open('GET', scheme_server + oavars.locations_uri_path, url_username=_args['username'], url_password=_args['password']).read()

        device_data = {}
        for p in _args:
            if p == 'api_protocol' or p == 'api_server' or p == 'username' or p == 'password':
                continue
            if p == 'collection':
                if _args[p] == "devices":
                    collection_type = "devices"
                    module_args_url = scheme_server + oavars.device_uri_path + "?format=json&properties=system.id,system.fqdn"
                elif _args[p] == "location":
                    raise AnsibleActionFail("Sorry but the option '%s' is not ready yet" % p)
                    # collection_type = "locations"
                    # module_args_url = scheme_server + oavars.locations_uri_path
                elif _args[p] == "fields":
                    raise AnsibleActionFail("Sorry but the option '%s' is not ready yet" % p)
                    # collection_type = "fields"
                    # module_args_url = scheme_server + oavars.fields_uri_path
            else:
                module_args[p] = _args[p]

        try:
            collection_type
        except NameError:
            raise AnsibleActionFail("Error: You have not specified a valid update type.\n\nCurrently supported are:\n- devices")

        # parse given fields and map them according to their definitions
        try:
            for o in _args['attributes']:
                for lk, v in o.items():
                    device_data[lk] = v
        except KeyError as e:
            raise AnsibleActionFail("Error: 'attributes' option is missing.\nError was: %s" % to_native(e))
        except Exception as e:
            raise AnsibleActionFail("You have not specified valid 'attributes'.\nError was: %s" % to_native(e))

        try:
            api_cookie = oaget.logon_api(self, uri=scheme_server + oavars.logon_uri_path,
                                         usr=_args['username'], pw=_args['password'],
                                         tmp=tmp, task_vars=task_vars,
                                         parsed_args=module_args)
        except Exception as e:
            raise AnsibleActionFail("Problem occured during login\n\nError message:\n%s\n\n%s" % (to_native(e), oavars.default_error_hint))

        # set cookie and target url
        module_args['method'] = "GET"
        module_args['headers'] = {}
        module_args['headers']['Cookie'] = api_cookie
        module_args['url'] = module_args_url

        # fetch data from corresponding API endpoint
        if collection_type == "devices":
            try:
                module_return = oadev.update(self, scheme_server=scheme_server,
                                             device_data=device_data,
                                             tmp=tmp, task_vars=task_vars,
                                             module_args=module_args)
                result.update(module_return)
            except Exception as e:
                raise AnsibleActionFail("Problem occured while updating attributes for >" + device_data['fqdn']
                                        + "<\n\nError message was:\n%s\n\n%s" % (to_native(e), oavars.default_error_hint))
        # elif collection_type == "location":
            # api_content = oaget.api(self, tmp=tmp, task_vars=task_vars, parsed_args=module_args)
        # elif collection_type == "field":
            # api_content = oaget.api(self, tmp=tmp, task_vars=task_vars, parsed_args=module_args)
        else:
            # raise AnsibleActionFail("Missing required option: you must set device, location or field!")
            raise AnsibleActionFail("Missing required option: you must set >device<")

        return result
