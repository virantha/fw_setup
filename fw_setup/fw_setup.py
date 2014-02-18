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
import yaml


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

        print self.config
        if self.debug:
            logging.basicConfig(level=logging.DEBUG, format='%(message)s')

        if self.verbose:
            logging.basicConfig(level=logging.INFO, format='%(message)s')


    def import_smoothwall(self, config):
        with open('config/import_smoothwal.dhcp.txt') as f:
            for line in f:
                (hostname, mac, ip, desc, enabled) = line.strip().split(',')
                ip = ip.split('.')[-1]
                config['dhcp']['fixed'].append( { 
                        'mac':mac, 
                        'name': hostname,
                        'ip': ip,
                        'description':desc
                        })

        config['dhcp']['fixed'] = sorted(config['dhcp']['fixed'], key=lambda x: int(x['ip']))



    def go(self, argv):
        """ 
            The main entry point into FirewallSetup

            #. Do something
            #. Do something else
        """
        # Read the command line options
        self.get_options(argv)
        self.import_smoothwall(self.config)
        print self.config
        with open('config/ipfire_new.yml', 'w') as f:
            yaml.dump(self.config, f)


def main():
    script = FirewallSetup()
    script.go(sys.argv[1:])

if __name__ == '__main__':
    main()

