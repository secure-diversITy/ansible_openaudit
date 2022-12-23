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

DOCUMENTATION = """
---
module: update
short_description: Updates defined attributes for an existing device in Open-AudIT
description:
    - Updates any field of an existing device object in Open-AudIT.
    - This plugin is B(not) developed by Firstwave (was Opmantek until 2021) nor has any commercial relationship to them.
    - It is simply a contribution to the community in the hope it is useful and of course without any warranties.
author: Thomas Fischer (@se-di)
version_added: '1.1.0'
requirements:
    - python3 >= '3.5'
    - python-requests
    - Open-AudIT >= '4.3.4'
options:
    api_server:
        description: FQDN or IP of the Open-AudIT server API
        required: true
    api_protocol:
        description: Protocol to be used for accessing the Open-AudIT server API
        choices:
            - http
            - https
        required: true
    username:
        description:
            - Username for logging into the API.
            - Avoid storing sensitive data in clear text by using e.g. Ansible Vault
        required: true
    password:
        description:
            - Password for logging into the API.
            - Avoid storing sensitive data in clear text by using e.g. Ansible Vault
        required: true
    collection:
        description:
            - The collection name/type.
            - For details & examples check the L(documentation,https://github.com/secure-diversITy/ansible_openaudit_inventory/wiki).
        choices:
            - devices
        required: true
    attributes:
        description: A list of device key/value pairs
        required: true
        suboptions:
            fqdn:
                description: The FQDN of the device to be updated (must match the field 'FQDN' of that device within Open-AudIT)
                required: true
            fields:
                description:
                    - A dictionary of field names including their target values.
                    - Keys are the corresponding Open-AudIT field name, values will be set accordingly.
                    - Any field name(!) you wish to update. Value can be a string or integer but ensure it is valid in Open-AudIT (check documentation).
                    - Must be 100% as the name in Open-AudIT.
                    - Special chars must be quoted.
                    - If you've updating trouble on custom fields check
                    - the L(documentation,https://github.com/secure-diversITy/ansible_openaudit_inventory/wiki).
                required: true
                type: dict
seealso:
    - name: Plugin documentation
      description: Detailed examples and guidelines for this plugin
      link: https://github.com/secure-diversITy/ansible_openaudit_inventory/wiki
    - name: Open-AudIT
      description: Official Open-AudIT product page
      link: https://firstwave.com/products/network-discovery-and-inventory-software/
    - name: Open-AudIT API
      description: Official Open-AudIT API documentation
      link: 'https://community.opmantek.com/display/OA/The+Open-AudIT+API'
"""

EXAMPLES = r'''
See L(documentation,https://github.com/secure-diversITy/ansible_openaudit_inventory/wiki)
'''

# required imports
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.sedi.openaudit.plugins.module_utils.common import OA_vars as oavars
from ansible_collections.sedi.openaudit.plugins.module_utils.common import OA_get as oaget
from ansible_collections.sedi.openaudit.plugins.module_utils.device import OA_device as oadev
# from ansible.module_utils import urls as url
from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleError, AnsibleAction, _AnsibleActionDone, AnsibleActionFail
from ansible.module_utils._text import to_native

__metaclass__ = type


class ActionModule(ActionBase):

    def run(self, tmp=None, task_vars=None):

        result = super(ActionModule, self).run(tmp, task_vars)
        _args = self._task.args.copy()
        module_args = dict()

        scheme_server = _args['api_protocol'] + "://" + _args['api_server']

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

        try:
            for o in _args['attributes']:
                for l, v in o.items():
                    device_data[l] = v
        except KeyError as e:
            raise AnsibleActionFail("Error: 'attributes' option is missing.")
        except Exception as e:
            raise AnsibleActionFail("You have not specified valid 'attributes'.\nError was: %s" % to_native(e))

        try:
            api_cookie = oaget.logon_api(self, uri=scheme_server + oavars.logon_uri_path,
                                         usr=_args['username'], pw=_args['password'],
                                         tmp=tmp, task_vars=task_vars,
                                         parsed_args=module_args)
            # result.update(e.module_return)
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
            except AnsibleError as e:
                raise AnsibleActionFail("Problem occured while updating attributes for >" + device_data['fqdn'] + "<\n\nError message was:\n%s\n\n%s" % (to_native(e), oavars.default_error_hint))
        elif collection_type == "location":
            api_content = oaget.api(self, tmp=tmp, task_vars=task_vars, parsed_args=module_args)
        elif collection_type == "field":
            api_content = oaget.api(self, tmp=tmp, task_vars=task_vars, parsed_args=module_args)
        else:
            raise AnsibleActionFail("Missing required option: you must set device, location or field!")

        return result
