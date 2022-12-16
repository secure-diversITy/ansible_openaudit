# -*- coding: utf-8 -*-
#########################################################################################
#
# Copyright:
#   - 2022 T.Fischer <mail |at| sedi -DOT- one>
#
# License:
#   - CC BY-SA 4.0 (http://creativecommons.org/licenses/by-sa/4.0/)
#
#########################################################################################

DOCUMENTATION = """
---
module: sedi.openaudit.inventory
plugin_type: inventory
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
version_added: '1.0'
requirements:
    - python3 >= '3.5'
    - python3-requests
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
        description: Username for logging into the API
        required: true
    oa_password:
        description: Password for logging into the API
        required: true
    oa_fieldsTranslate:
        description:
            - A dictionary of all C(Ansible variable <-> field-id) mappings.
            - Must match with the fields id which can be achieved from C(Manage->Fields) within the Open-AudIT Web UI.
            - For details & examples check the L(documentation,https://github.com/secure-diversITy/ansible_openaudit_inventory/wiki).
        elements: dict
        suboptions:
            freely-selectable-variable-name:
                description:
                    - Any variable name you wish to use in Ansible.
                    - It becomes part of the hostvars for a host when you add it to a device in Open-AudIT.
                type: int
                choices:
                    - C(<Open-AudIT-field-id>)
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
# extends_documentation_fragment:
#    - inventory_cache

EXAMPLES = r'''

add this module to your ansible.cfg:

[inventory]
enable_plugins = sedi.openaudit.inventory


Example hosts.openaudit.yaml file:

---
plugin: sedi.openaudit.inventory
oa_api_server: openaudit.myserver.com
oa_api_proto: https
oa_username: "{{ vault_api_server_user }}"
oa_password: "{{ vault_api_server_password }}"

oa_fieldsTranslate:
    cmdb_foo: 7
    myvar_for_ansible: 13
    my_other_var: 21

groups:
    edge_devices: "'edge' in inventory_hostname"
    backup_servers: inventory_hostname.startswith('backup')
    non_gigabyte_devices: cmdb_manufacturer.upper() != "GIGABYTE"

keyed_groups:
    - prefix: FAI_profile
      key: cmdb_fai_profile
    - prefix: VENDOR
      key: cmdb_manufacturer.lower()

compose:
   ansible_host: ip4_address

'''

# required imports
import requests
import json
import re
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable
from ansible.utils.vars import combine_vars

# minimal expected length for variable / fields content
min_var_chars = 2

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

# build properties list we want to fetch based on devicesTranslate
devp = []
for pk, pv in devicesTranslate.items():
    devp.append(pk)
devicesproperties = ','.join(devp)

# API URI paths
logon_uri_path = '/open-audit/index.php/logon'
device_uri_path = '/open-audit/index.php/devices?format=json&properties=' + devicesproperties
fields_uri_path = '/open-audit/index.php/devices?format=json&properties=system.id&sub_resource=field'
locations_uri_path = '/open-audit/index.php/locations?&format=json'
# orgs_uri_path = '/open-audit/index.php/orgs?&format=json'

# class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):


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
        oa_login = oaSession.post(base_uri + logon_uri_path, data={'username': self.get_option('oa_username'), 'password': self.get_option('oa_password')})
        if oa_login.status_code != 200:
            raise Exception("Could not login to the API at " + base_uri + "! Check servername and credentials...")

    def get_oa_data(self, base_uri: str, uri_path: str):
        """
        fetch data from given api url
        """
        OAdata = oaSession.get(base_uri + uri_path, cookies=oa_login.cookies)
        jsonData = json.loads(OAdata.text)
        jsonDataList = jsonData['data']

        if OAdata.status_code != 200:
            raise Exception("Could not access " + uri_path + "! Check servername and credentials...")

        # Check again if we have valid data
        for resp in jsonDataList:
            if resp is False:
                raise Exception("Error while accessing the API")

        return jsonDataList

    def to_valid_group_name(self, name):
        """
        we do not use to_safe_group_name from ansible.inventory.group
        as it still allows several bad chars like @ or even spaces which makes
        it harder to work with these
        """
        sname = re.compile(r'^[\d\W]|[^\w]').sub("_", name)
        return sname

    def to_json(self):
        return self.json

    # def parse(self, inventory, loader, path, cache=True):
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

        # allow caching
        # self.load_cache_plugin()
        # cache_key = self.get_cache_key(path)

        # cache may be True or False at this point to indicate if the inventory is being refreshed
        # get the user's cache option too to see if we should save the cache if it is changing
        # user_cache_setting = self.get_option('cache')

        # read if the user has caching enabled and the cache isn't being refreshed
        # attempt_to_read_cache = user_cache_setting and cache
        # update if the user has caching enabled and the cache is being refreshed; update this value to True if the cache has expired below
        # cache_needs_update = user_cache_setting and not cache

        # attempt to read the cache if inventory isn't being refreshed and the user has caching enabled
        # if attempt_to_read_cache:
        #    try:
        #        results = self._cache[cache_key]
        #    except KeyError:
        #        # This occurs if the cache_key is not in the cache or if the cache_key expired, so the cache needs to be updated
        #        cache_needs_update = True
        # if not attempt_to_read_cache or cache_needs_update:
        #    # parse the provided inventory source
        #    results = self.get_inventory()
        # if cache_needs_update:
        #    self._cache[cache_key] = results
        # submit the parsed data to the inventory object (add_host, set_variable, etc)
        # self.populate(results)

        # build first part of the uri based on the user config
        api_base_uri = self.get_option('oa_api_proto') + '://' + self.get_option('oa_api_server')

        # login first
        self.login_oa(api_base_uri)

        # fetch all data
        oaDataList = self.get_oa_data(api_base_uri, device_uri_path)
        oaFieldsList = self.get_oa_data(api_base_uri, fields_uri_path)
        oaLocationsList = self.get_oa_data(api_base_uri, locations_uri_path)

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
            for k in devicesTranslate:
                try:
                    hostsDict[devicesTranslate[k]] = i['attributes'][k]
                except Exception:
                    self.display.vvvv('Open-AudIT Device #' + str(i['attributes']['system.id']) + " Does not have " + str(k))
                    continue

            # add host and the base vars to the ansible inventory based on the FQDN
            host = hostsDict['cmdb_fqdn']
            self.inventory.add_host(host)
            for dkey, dvar in hostsDict.items():
                self.inventory.set_variable(host, dkey, dvar)

            # add location based vars before fields
            # that way it will be possible to overwrite them by host vars
            for loc in oaLocationsList:
                if not hostsDict['cmdb_location_id'] and not hostsDict['cmdb_org_id']:
                    continue
                else:
                    for lk, lv in locationsTranslate.items():
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
