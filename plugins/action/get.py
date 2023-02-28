# -*- coding: utf-8 -*-
#####################################################################################################
#
# Copyright:
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
from ansible_collections.sedi.openaudit.plugins.module_utils.common import OA_misc as oamisc
from ansible_collections.sedi.openaudit.plugins.module_utils.device import OA_device as oadev
from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail
from ansible.module_utils._text import to_native


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):

        result = super(ActionModule, self).run(tmp, task_vars)
        _args = self._task.args.copy()
        scheme_server = _args['api_protocol'] + "://" + _args['api_server']

        # parse given module parameters
        module_args = oamisc.parse_args(self, scheme_server, _args)

        # set and remove internal type value
        collection_type = module_args['collection_type']
        del module_args['collection_type']

        try:
            collection_type
        except NameError:
            raise AnsibleActionFail("Error: You have not specified a valid update type.\n\nCurrently supported are:\n- >devices<")

        # create dict based on attributes
        device_data = oamisc.create_attrs_dict(self, attrs=_args['attributes'])

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
        module_args['url'] = scheme_server + oavars.device_uri_path + '/' + str(task_vars['oa.id']) + "?format=json&include=all"
        # 20?format=json&include=all' | jq .included[].attributes

        # fetch data from corresponding API endpoint
        if collection_type == "devices":
            try:
                module_return = oadev.get_field(self, field=device_data['field'],
                                                tmp=tmp, task_vars=task_vars,
                                                margs=module_args, return_valid_fields=True)
                if module_return is None:
                    raise KeyError("The requested field >%s< does not exist in Open-AudIT!" % device_data['field'])
                else:
                    result.update(value=module_return, changed=True)
            except Exception as e:
                raise AnsibleActionFail("Problem occured while reading attributes for >" + device_data['fqdn']
                                        + "<\n\nError message was:\n%s\n\n%s" % (to_native(e), oavars.default_error_hint))
        else:
            # raise AnsibleActionFail("Missing required option: you must set device, location or field!")
            raise AnsibleActionFail("Missing required option: >devices<")

        return result
