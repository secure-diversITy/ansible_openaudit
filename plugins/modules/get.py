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

DOCUMENTATION = """
---
module: get
short_description: Request a given field/attribute of an existing device in Open-AudIT
description:
    - Returns the value of a requested field/attribute in Open-AudIT.
    - This plugin is B(not) developed by Firstwave (was Opmantek until 2021) nor has any commercial relationship to them.
    - It is simply a contribution to the community in the hope it is useful and of course without any warranties.
author: Thomas Fischer (@se-di)
version_added: '2.1.0'
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
        description: A valid Open-AudIT field/attribute name of a collection type (see collection)
        required: true
        suboptions:
            fqdn:
                description: The FQDN of the device to be updated (must match the field 'FQDN' of that device within Open-AudIT)
                required: true
            field:
                description:
                    - The requested field/attribute. Must be available in Open-AudIT as predefined attribute or
                    - from your own field mappings in "oa_fieldsTranslate" (e.g. in ./inventories/dynamic/inventory.openaudit.yml).
                    - The easiest way to get a list of all valid Open-AudIT fields is specifying an invalid key
                    - (e.g. set C(oa.invalidkey)) and it will print all available (internal, i.e. not custom) field names.
                    - Important is that you have to set exactly the value(!)/value store(!) as it is defined in Open-AudIT.
                    - For custom field lists C(fields -> List -> Values) or internal lists in C(attributes -> list -> Value store)
                required: true
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

RETURN = r'''
value:
    description: The value of the requested field/attribute or if invalid a list of valid fields/attributes
    returned: success
    type: str
    sample: 10.1.1.123
'''

EXAMPLES = r'''
For more examples and details check L(documentation,https://github.com/secure-diversITy/ansible_openaudit_inventory/wiki)

---
- name: Request a field in OA
  gather_facts: false
  hosts: all

  tasks:
    - name: "Get status info for {{ inventory_hostname }}"
      connection: local
      become: no
      sedi.openaudit.get:
        api_server: my.openauditserver.local
        api_protocol: https
        username: "{{ vault_api_server_user }}"
        password: "{{ vault_api_server_password }}"
        return_content: true
        validate_certs: false
        collection: devices
        attributes:
            - fqdn: "{{ inventory_hostname }}"
              field: oa.status

'''
