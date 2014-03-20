#!/usr/bin/env python2.7
# Copyright 2014 Virantha Ekanayake All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""
    Plugins for different firewalls and services must inherit from this class
"""

import logging

import imp
import pkgutil
import os


class Plugin(object):
     
    class __metaclass__(type):
             
        def __init__(cls, name, base, attrs):
            if not hasattr(cls, 'registered'):
                cls.registered = {}
            else:
                #cls.registered.append(cls)
                cls.registered[name] = cls
                                     
    @classmethod
    def load(cls, *paths):
        paths = list(paths)
        cls.registered = {}
        for _, name, _ in pkgutil.iter_modules(paths):
            fid, pathname, desc = imp.find_module(name, paths)
            try:
                imp.load_module(name, fid, pathname, desc)
            except Exception as e:
                logging.warning("could not load plugin module '%s': %s",
                                pathname, e.message)
            if fid:
                fid.close()

    def _write_file(self, dest_dir, filename, contents):
        fn = os.path.join(dest_dir, filename)
        print ("Writing %s..." % fn)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        with open(fn, 'w') as f:
            f.write(contents)

    def _get_dhcp_entries(self, config):
        clients = []
        for intrf in config['dhcp']:
            print("Emitting dhcp fixed leases for %s" % intrf['interface'])
            prefix = intrf['prefix']
            if prefix!= "" and not prefix.endswith('.'): prefix += '.'
            for client in intrf['leases']:
                logging.debug(client)
                client['desc'] = client.setdefault('desc', '')
                client['remark'] = "%(name)s %(desc)s" % client
                if client['en']: client['enabled'] = 'on'
                else: client['enabled'] = 'off'
                client['prefix'] = prefix
                clients.append(client)
                
        return clients

    def _get_dns_entries(self, config):
        """
            Add the following to the hosts list and return a dict:
             
            * DHCP fixed leases ('dhcp' section)
            * Static hosts ('dns'-> 'hosts' section)
            * Static host aliases ('dns'-> 'aliases' section)

            :rval: dict of name to ip mapping
        """
        dns_name = {}
        # Go through fixed leases and add them first
        for intrf in config['dhcp']:
            prefix = intrf['prefix']
            if prefix!= "" and not prefix.endswith('.'): prefix += '.'
            for client in intrf['leases']:
                client['desc'] = client.setdefault('desc', '')
                client['remark'] = "%(name)s %(desc)s" % client
                client['enabled'] = (client['en'])
                client['prefix'] = prefix
                dns_name[client['name']] = '%(prefix)s%(ip)s' % client

        # Now, add in the ones from the static explicit dns mapping
        for host in config['dns']['hosts']:
            dns_name[host['name']] = '%s%s' % (config['dns']['prefix'],host['ip'])
        # Now, add in all the aliases
        for alias_entry in config['dns']['aliases']:
            ip = dns_name[alias_entry['hostname']]
            for alias in alias_entry['alias']:
                dns_name[alias] = ip

        # TODO: Honor enabled entries
        return dns_name

