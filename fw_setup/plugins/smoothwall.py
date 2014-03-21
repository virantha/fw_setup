
from plugin import Plugin
from fabric.api import env, run, cd, lcd, put
import os
import requests
import mechanize
class Smoothwall(Plugin):
    """
        Currently implements:

        * DHCP fixed leases
        * DNS static hosts for fixed leases and aliases

    """
    def __init__ (self, config, dest_dir='smoothwall'):
        self.config = config
        self.dest_dir = dest_dir

    def emit_dns(self):
        dns_name = self._get_dns_entries(self.config)
        dns_entries = []

        for name, ip in dns_name.items():
            dns_entries.append('%s,%s,on' % (ip, name))

        self._write_file(self.dest_dir, 'dns.txt', '\n'.join(dns_entries))

    def emit_dhcp(self):
        clients = self._get_dhcp_entries(self.config)
        for interface in clients:
            leases = []
            for client in clients[interface]:
                leases.append('%(name)s,%(mac)s,%(prefix)s%(ip)s,%(remark)s,%(enabled)s' % client)
                
            self._write_file(self.dest_dir, 'dhcp_%s.txt' % interface, ('\n'.join(leases)))

    def emit_portfw(self):
        rules = self._get_portfw(self.config)

        # Check to make sure each destination is present
        dns_names = self._get_dns_entries(self.config)
        for rule in rules:
            if not rule['dest'] in dns_names:
                print("WARNING: Port forwarding rule %s -> %s:%s is not a valid host" % (rule['port'], rule['dest'], rule['dest_port']))

        my_rules = []
        for rule in rules:
            rule['ip'] = dns_names[rule['dest']]
            my_rules.append('%(type)s,%(src)s,%(port)s,%(ip)s,%(dest_port)s,on,%(dest)s' % rule)
        self._write_file(self.dest_dir, 'port_fw.txt', ('\n'.join(my_rules)))



    def upload_files(self):
        fwvars = self.config['firewall']
        env.host_string = "%s@%s:%s" % (fwvars['username'], fwvars['ip'], fwvars['port'])
        with cd('/var/smoothwall'), lcd(self.dest_dir):
            for interface in self.config['dhcp']:
                intrf = interface['interface']
                put('dhcp_%s.txt' % intrf, 'dhcp/staticconfig-%s' % intrf)
            put('dns.txt', 'hosts/config')
            put('port_fw.txt', 'portfw/config')

        url = 'http://%s:81/cgi-bin/dhcp.cgi' % fwvars['ip']
        
        print ("Calling firewall dhcp update on web interface")
        # I couldn't figure out how to submit the form and make it work with smoothwall
        # So just call the internal functions
        run('/usr/bin/smoothwall/writedhcp.pl') 
        run('perl -I/usr/lib/smoothwall -Msmoothd -e \'message("dhcpdrestart");\'')

        print ("Calling firewall dns update using rebuildhosts")
        run('/usr/bin/smoothwall/writehosts.pl')
        run('perl -I/usr/lib/smoothwall -Msmoothd -e \'message("dnsproxyhup");\'')

        print ("Calling firewall port-fw using setincoming")
        run('perl -I/usr/lib/smoothwall -Msmoothd -e \'message("setincoming");\'')
