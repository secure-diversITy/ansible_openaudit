# -*- coding: utf-8 -*-
#####################################################################################################
#
# Copyright:
#   - 2022 T.Fischer <mail |at| sedi -DOT- one>
#
# License: GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
#####################################################################################################

from __future__ import (absolute_import, division, print_function)

import json
from ansible.errors import AnsibleActionFail
from ansible.module_utils._text import to_native
from ansible_collections.sedi.openaudit.plugins.module_utils.common import OA_vars as oavars
from ansible_collections.sedi.openaudit.plugins.module_utils.common import OA_get as oaget
__metaclass__ = type


class OA_device():

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
            raise ValueError
        except Exception as e:
            raise Exception("Could not find matching device id for FQDN")

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
            raise AnsibleActionFail("%s" % to_native(e))

        device_id = str(parsed_device_data['system.id'])

        # fetch all data for that device id
        # module_args['url'] = scheme_server + oavars.device_uri_path + "/" + device_id + "?format=json"
        # device_content = oaget.api(self, tmp=tmp, task_vars=task_vars, parsed_args=module_args)
        # print(device_content)
        # dev_dict = {k:v for e in device_content['data'] for (k,v) in e.items()}
        # meta_token = device_content['meta']['access_token']

        # curl .. -d 'data={"data":{"id":"161","type":"devices","attributes":{"org_id":"2"}}}'
        body_data = {}
        body_data['data'] = {}
        body_data['data']['id'] = device_id
        body_data['data']['type'] = "devices"
        body_data['data']['attributes'] = device_data['fields']

        try:
            module_args['method'] = "PATCH"
            module_args['url'] = scheme_server + oavars.device_uri_path + "/" + device_id
            module_args['body'] = "data=" + json.dumps(body_data)
            module_return = oaget.api(self, tmp=tmp, task_vars=task_vars, parsed_args=module_args)
        except Exception as e:
            raise AnsibleActionFail("Problem occured while updating the following attributes:\n" + json.dumps(body_data) + "\n%s" % to_native(e))

        return module_return
