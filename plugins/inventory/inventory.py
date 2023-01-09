# -*- coding: utf-8 -*-
##############################################################################################
#
# Copyright:
#   - 2022 T.Fischer <mail |at| sedi -DOT- one>
#   - 2023 T.Fischer <mail |at| sedi -DOT- one>
#
# License:
# GNU General Public License v3.0 (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
##############################################################################################

DOCUMENTATION = """
---
name: inventory
short_description: Returns a dynamic host inventory from Open-AudIT
description:
    - This inventory plugin will login to Open-AudIT and downloads the device list,
    - fetches all fields, locations and orgs for all devices,
    - maps all fields to (defined) human readable names
    - and finally returns an Ansible inventory.
    - It supports using custom fields in Open-AudIT which can then be used in Ansible as variables.
    - This plugin is B(not) developed by Firstwave (was Opmantek until 2021) nor has any commercial relationship to them.
    - It is simply a contribution to the community in the hope it is useful and of course without any warranties.
author: Thomas Fischer (@se-di)
version_added: '1.0.0'
requirements:
    - python3 >= '3.5'
    - python-requests
    - Open-AudIT >= '4.3.4'
options:
    plugin:
        description: token that ensures this is a config file which is part of this plugin.
        required: true
        choices: ['sedi.openaudit.inventory']
    oa_api_server:
        description: FQDN or IP address of the Open-AudIT server API
        required: true
    oa_api_proto:
        description: Protocol to be used for accessing the Open-AudIT server API
        choices:
            - http
            - https
        required: true
    oa_username:
        description:
            - Username for logging into the API.
            - Avoid storing sensitive data in clear text by using inline encrypted variables.
            - e.g. C(ansible-vault encrypt_string 'this-is-a-real-username' --name oa_username --ask-vault-pass)
            - At this early stage full encrypted vault files are not accessible.
        required: true
    oa_password:
        description:
            - Password for logging into the API.
            - Avoid storing sensitive data in clear text by using inline encrypted variables.
            - e.g. C(ansible-vault encrypt_string 'this-is-a-realpassword!' --name oa_password --ask-vault-pass)
            - At this early stage full encrypted vault files are not accessible.
        required: true
    oa_fieldsTranslate:
        description:
            - A dictionary of all C(Ansible variable <-> field-id) mappings.
            - Must match with the fields id which can be achieved from C(Manage->Fields) within the Open-AudIT Web UI.
            - For details & examples check the L(documentation,https://github.com/secure-diversITy/ansible_openaudit_inventory/wiki).
        suboptions:
            freely-selectable-variable-name:
                description:
                    - Any variable name you wish to use in Ansible.
                    - It becomes part of the hostvars for a host when you add it to a device in Open-AudIT.
                type: int
        required: false
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
extends_documentation_fragment:
    - constructed
"""

EXAMPLES = r'''
'''

# required imports
import requests
import re
from ansible_collections.sedi.openaudit.plugins.module_utils.common import OA_vars as oavars
from ansible_collections.sedi.openaudit.plugins.module_utils.common import OA_get as oaget
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable
from ansible.utils.vars import combine_vars

# minimal expected length for variable / fields content
min_var_chars = 2


class InventoryModule(BaseInventoryPlugin, Constructable):

    NAME = 'sedi.openaudit.inventory'

    def verify_file(self, path):
        if super(InventoryModule, self).verify_file(path):
            if path.endswith(('openaudit.yaml', 'openaudit.yml', 'oa.yaml', 'oa.yml')):
                return True
            else:
                self.display.vvv('Skipping due to inventory source not ending in "openaudit.yml" nor "oa.yml"')
        return False

    def login_oa(self, base_uri: str):
        """
        Create a session to the Open-AudIT API and store as cookie
        """
        global oaSession
        global oa_login
        oaSession = requests.Session()
        oa_login = oaSession.post(base_uri + oavars.logon_uri_path,
                                  data={'username': self.get_option('oa_username'), 'password': self.get_option('oa_password')})
        if oa_login.status_code != 200:
            raise Exception("Could not login to the API at " + base_uri + "! Check servername and credentials...")

    def to_valid_group_name(self, name):
        """
        we do not use to_safe_group_name from ansible.inventory.group
        as it still allows several bad chars like @ or even spaces which makes
        it harder to work with these
        """
        sname = re.compile(r'^[\d\W]|[^\w]').sub("_", name)
        return sname

    def parse(self, inventory, loader, path, cache=None):
        """
        parse all data and create a dictionary containing all joined data for a host

        will:
            - loop over all devices
            - loop over all properties
            - loop over available locations and update host vars with found location name + org
            - loop over all fields and set all valid (see fieldsTranslate) as a hostvar
        """

        # call base method to ensure properties are available for use with other helper methods
        super(InventoryModule, self).parse(inventory, loader, path)

        self._read_config_data(path)

        # build first part of the uri based on the user config
        api_base_uri = self.get_option('oa_api_proto') + '://' + self.get_option('oa_api_server')

        # login first
        self.login_oa(api_base_uri)

        # fetch all data
        oaDataList = oaget.oa_data(self, oaSession, oa_login, api_base_uri, oavars.devices_uri_path)
        oaFieldsList = oaget.oa_data(self, oaSession, oa_login, api_base_uri, oavars.fields_uri_path)
        oaLocationsList = oaget.oa_data(self, oaSession, oa_login, api_base_uri, oavars.locations_uri_path)

        # read config + display debug info
        conf_strict = self.get_option('strict')
        conf_compose = self.get_option('compose')
        conf_hostgrps = self.get_option('groups')
        conf_keyedgrps = self.get_option('keyed_groups')
        self.display.vvv('config_file -> compose: ' + str(conf_compose))
        self.display.vvv('config_file -> host groups: ' + str(conf_hostgrps))
        self.display.vvv('config_file -> keyed host groups: ' + str(conf_keyedgrps))

        # iterate over ever device entry
        for i in oaDataList:
            hostsDict = {}

            # first of all get the system values and create a dict based on the translated items
            for k in oavars.devicesTranslate:
                try:
                    hostsDict[oavars.devicesTranslate[k]] = i['attributes'][k]
                except Exception:
                    self.display.vvvv('Open-AudIT Device #' + str(i['attributes']['system.id']) + " Does not have " + str(k))
                    continue

            # add host and the base vars to the ansible inventory based on the FQDN
            host = hostsDict['cmdb_fqdn']
            # handle empty FQDN (skip entry, print warning)
            if len(str(host)) < 4:
                self.display.vvv('WARNING: host >' + host + '< with id >' + str(hostsDict['cmdb_oa_id']) + '< seems not having a FQDN set')
                continue
            # add host to inventory list including base vars
            self.inventory.add_host(host)
            for dkey, dvar in hostsDict.items():
                self.inventory.set_variable(host, dkey, dvar)

            # add location based vars before fields
            # that way it will be possible to overwrite them by host vars
            for loc in oaLocationsList:
                if not hostsDict['cmdb_location_id'] and not hostsDict['cmdb_org_id']:
                    continue
                else:
                    for lk, lv in oavars.locationsTranslate.items():
                        if hostsDict['cmdb_location_id'] != loc['attributes']['id']:
                            continue
                        if len(str(loc['attributes'][lk])) < min_var_chars:
                            continue
                        # the special field suite can hold multiple key=value pairs
                        if lk == "suite" and ";" in loc['attributes'][lk]:
                            la = loc['attributes'][lk].split(';')
                            lodict = dict(s.split('=', 1) for s in la)
                            for lok, lov in lodict.items():
                                self.inventory.set_variable(host, lok, lov)
                                hostsDict[lok] = lov
                        else:
                            self.inventory.set_variable(host, lv, loc['attributes'][lk])
                            hostsDict[lv] = loc['attributes'][lk]

            # apply any local defined (config file) variables
            # overwrites location / group variables coming from Open-AudIT
            # can be overwritten by fields (i.e. like ansible host variables)
            hostvars = inventory.hosts[host].get_vars()
            self._set_composite_vars(conf_compose, hostvars, host, strict=True)

            # now walk through the list of fields
            # (overwrites location/site based variables from oaLocationsList)
            fTopt = self.get_option('oa_fieldsTranslate')
            if not fTopt:
                continue
            else:
                for f in oaFieldsList:
                    # proceed only when the fields matching the current host object
                    if f['attributes']['system.id'] == i['attributes']['system.id']:
                        for fk, fv in fTopt.items():
                            # proceed only when the field is a supported item
                            if f['attributes']['field.fields_id'] == fv and len(f['attributes']['field.value']) >= min_var_chars:
                                # special handling for free form variable field (separated by semicolons)
                                if fk == "free_form_vars" and ";" in f['attributes']['field.value']:
                                    a = f['attributes']['field.value'].split(';')
                                    fkdict = dict(s.split('=') for s in a)
                                    for fdk, fdv in fkdict.items():
                                        self.inventory.set_variable(host, fdk, fdv)
                                else:
                                    self.inventory.set_variable(host, fk, f['attributes']['field.value'])
                                hostsDict[fk] = f['attributes']['field.value']

            # add hosts to their static group based on org and/or location
            # prob: atm (i.e. Open-AudIT v4.3.4) a user can select even locations NOT bound to the selected
            # organisation! That way you will can easily see wrong group mappings when a user picks the wrong location
            # not belonging to that org.. Hopefully get fixed by SUPPORT-10106
            constructed_grp_name = []
            if hostsDict['cmdb_location'] and hostsDict['cmdb_org']:
                constructed_grp_name.append(self.to_valid_group_name(hostsDict['cmdb_org']))
                constructed_grp_name.append(self.to_valid_group_name(hostsDict['cmdb_org'] + "__" + hostsDict['cmdb_location']))
            else:
                constructed_grp_name.append(self.to_valid_group_name(hostsDict['cmdb_org']))

            for cg in constructed_grp_name:
                self.inventory.add_group(cg)
                self.display.vvvv("adding: " + host + " to group: " + cg)
                self.inventory.add_host(host, group=cg)

            hostvars = inventory.hosts[host].get_vars()

            # from config file:
            # add host to composed and/or keyed groups and apply any variables defined there
            self._add_host_to_composed_groups(conf_hostgrps, hostvars, host, strict=conf_strict)
            self._add_host_to_keyed_groups(conf_keyedgrps, hostvars, host, strict=conf_strict)

            self.display.vvvv('hostsDict: ' + str(hostsDict))
            self.display.vvvv('hostvars: ' + str(hostvars))
            self.display.vvvv('in groups: ' + str(inventory.hosts[host].get_groups()))