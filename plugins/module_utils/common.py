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


class OA_vars():

    # https://<server>/open-audit/index.php/devices
    # changes here likely require to change device_uri_path (add/remove properties)
    devicesTranslate = {
        'orgs.name': 'cmdb_org',
        'org_id': 'cmdb_org_id',
        'system.ip': 'cmdb_ip',
        'system.manufacturer': 'cmdb_manufacturer',
        'system.id': 'cmdb_oa_id',
        'system.fqdn': 'cmdb_fqdn',
        'system.status': 'cmdb_status',
        'system.location_id': 'cmdb_location_id'
    }

    # https://<server>/open-audit/index.php/locations
    locationsTranslate = {
        'orgs.name': 'cmdb_org',
        'orgs.id': 'l_cmdb_org_id',
        'name': 'cmdb_location',
        'suite': 'cmdb_location_vars',
    }

    # https://<server>/open-audit/index.php/groups
    groupsTranslate = {
        'groups.id': 'cmdb_group_id',
        'groups.description': 'cmdb_group_vars',
        'groups.name': 'cmdb_group_name',
    }

    # build properties list we want to fetch based on devicesTranslate
    devp = []
    for pk, pv in devicesTranslate.items():
        devp.append(pk)
    devicesproperties = ','.join(devp)

    # API URI paths
    logon_uri_path = '/open-audit/index.php/logon'
    device_uri_path = '/open-audit/index.php/devices'
    devices_uri_path = device_uri_path + '?format=json&properties=' + devicesproperties
    fields_uri_path = '/open-audit/index.php/devices?format=json&properties=system.id&sub_resource=field'
    locations_uri_path = '/open-audit/index.php/locations?&format=json'
    groups_base_uri_path = '/open-audit/index.php/groups'
    groups_list_uri_path = groups_base_uri_path + '?format=json&properties=groups.id,groups.description,groups.name'
    groups_execute_path = '/execute?format=json&properties=system.id,system.fqdn'

    # messages
    default_error_hint = "Check that:\n- your credentials are correct\n"\
                         "- the api_server and api_proto are set correctly\n"\
                         "- the device actually exists in Open-AudIT\n"\
                         "-'FQDN' field is set properly in Open-AudIT and within your task"
    documentation_link = "https://github.com/secure-diversITy/ansible_openaudit/wiki"


class OA_get():

    def logon_api(self, uri, usr, pw, task_vars, tmp, parsed_args):
        """
        logon to the API with username + password
        returns a valid authentication cookie
        """
        module_args = parsed_args
        module_args['method'] = "POST"
        module_args['body_format'] = "form-urlencoded"
        module_args['body'] = {}
        module_args['body']['username'] = usr
        module_args['body']['password'] = pw
        module_args['body']['enter'] = "Submit"
        module_args['url'] = uri

        try:
            module_return = self._execute_module(module_name='ansible.legacy.uri',
                                                 module_args=module_args,
                                                 task_vars=task_vars, tmp=tmp)
            if 'failed' in module_return or module_return['status'] != 200:
                raise ValueError("Could not login to the API at %s. Error message: %s" % (uri, module_return['msg']))
        except Exception as e:
            raise e

        return module_return['cookies_string']

    def api(self, task_vars, tmp, parsed_args):
        """
        do any API call based on the URI module
        so supports whatever the URI module supports
        returns the content as json object
        """
        module_args = parsed_args
        try:
            module_return = self._execute_module(module_name='ansible.legacy.uri',
                                                 module_args=module_args,
                                                 task_vars=task_vars, tmp=tmp)

            if 'failed' in module_return or module_return['status'] != 200:
                raise ValueError("API call error: %s" % module_return['msg'])
        except Exception as e:
            raise e

        return module_return['json']

    def oa_data(self, oaSession, oa_login, base_uri, uri_path):
        """
        inventory only. Use api() for modules (see above)
        fetches data from given api url
        """

        self.display.vvvv('checking the following remote uri: ' + uri_path)

        OAdata = oaSession.get(base_uri + uri_path, cookies=oa_login.cookies)
        jsonData = json.loads(OAdata.text)
        jsonDataList = jsonData['data']

        if OAdata.status_code != 200:
            raise Exception("Could not access %s ! Check servername and credentials..." % uri_path)

        # Check again if we have valid data
        if jsonDataList:
            for resp in jsonDataList:
                if resp is False:
                    raise Exception("Error while accessing the API")

            return jsonDataList
        else:
            return
