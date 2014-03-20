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

import argparse
import sys, os
import logging
import shutil

from version import __version__
from plugin import Plugin
import yaml
from fabric.api import env, run, cd, lcd, put

"""
   
.. automodule:: fw_setup
    :private-members:
"""

class FirewallSetup(object):
    """
        The main clas.  Performs the following functions:

    """

    def __init__ (self):
        """ 
        """
        self.config = None
        self._register_plugins()

    def _register_plugins(self):
        script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        Plugin.load(os.path.join(script_dir,"plugins"))
        for p, p_class in Plugin.registered.items():
            print("Registered output plugin type %s" % p) 

    def _get_config_file(self, config_file):
        """
           Read in the yaml config file

           :param config_file: Configuration file (YAML format)
           :type config_file: file
           :returns: dict of yaml file
           :rtype: dict
        """
        with config_file:
            myconfig = yaml.load(config_file)
        return myconfig


    def get_options(self, argv):
        """
            Parse the command-line options and set the following object properties:

            :param argv: usually just sys.argv[1:]
            :returns: Nothing

            :ivar debug: Enable logging debug statements
            :ivar verbose: Enable verbose logging
            :ivar config: Dict of the config file

        """
        p = argparse.ArgumentParser(
                description = "",
                epilog = "Firewall Setup version %s (Copyright 2014 Virantha Ekanayake)" % __version__,
                )

        p.add_argument('-d', '--debug', action='store_true',
            default=False, dest='debug', help='Turn on debugging')

        p.add_argument('-v', '--verbose', action='store_true',
            default=False, dest='verbose', help='Turn on verbose mode')

        p.add_argument('config', help='Server configuration yaml')

        args = p.parse_args(argv)

        self.debug = args.debug
        self.verbose = args.verbose
        self.config_filename = args.config

        with open(self.config_filename) as f:
            self.config = yaml.load(f)

        if self.debug:
            logging.basicConfig(level=logging.DEBUG, format='%(message)s')

        if self.verbose:
            logging.basicConfig(level=logging.INFO, format='%(message)s')

        logging.debug(self.config)



    def validate_dhcp_fixed_with_dns(self, my_config):
        """ Make sure that the dhcp fixed leases do not conflict with 
            the static dns hostnames.  If there is a conflict, or there is
            an identical hostname to ip mapping, then remove the one
            from the dns entries (since we'll propagate the dhcp fixed
            leases automatically to the hosts file when we push changes
            to the firewall)
        """
        config = my_config.copy()
        dhcp_name = {}
        dhcp_ip = {}
        dns_name = {}
        for entry in config['dhcp'][0]['leases']:
            dhcp_name[str(entry['name'])] = entry
            dhcp_ip[str(entry['ip'])] = entry
            # Also make sure desc and en is set
            entry['desc'] = entry.setdefault('desc','')
            entry['en'] = entry.setdefault('en', True)

        for entry in config['dns']['hosts']:
            dns_name[str(entry['name'])] = entry
       
        # dhcp ->   name:ip
        #    Remove all dns entries with matching name
        #
        # dhcp ->   name:ip
        # dns  ->   ip:some_name 
        #    Implies alias in dns, so just report it
        for name, entry in dns_name.items():
            if dhcp_name.has_key(name):
                print("Removing static host entry that is already present in dhcp (%s -> %s)" % (name, entry['ip']))
                config['dns']['hosts'].remove(entry)
            elif dhcp_ip.has_key(entry['ip']):
                print("Found DNS alias (%s) to fixed lease (%s -> %s)" % (name, entry['ip'], dhcp_ip[entry['ip']]['name']))
        return config



    def go(self, argv):
        """ 
            The main entry point into FirewallSetup

            #. Do something
            #. Do something else
        """
        # Read the command line options
        self.get_options(argv)
        self.config = self.validate_dhcp_fixed_with_dns(self.config)
           
        firewall = Plugin.registered['Ipfire'](self.config)
        
        firewall.emit_dns()
        firewall.emit_dhcp()
        firewall.upload_files()


def main():
    script = FirewallSetup()
    script.go(sys.argv[1:])

if __name__ == '__main__':
    main()

