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

DOCUMENTATION = """
---
module: set
short_description: Updates defined attributes for an existing device in Open-AudIT
description:
    - Updates any field of an existing device object in Open-AudIT.
    - This plugin is B(not) developed by Firstwave (was Opmantek until 2021) nor has any commercial relationship to them.
    - It is simply a contribution to the community in the hope it is useful and of course without any warranties.
author: Thomas Fischer (@se-di)
version_added: '1.2.0'
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
