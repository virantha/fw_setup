
from plugin import Plugin
from fabric.api import env, run, cd, lcd, put
import os
import requests
import mechanize
class Ipfire(Plugin):

    def __init__ (self, config, dest_dir='ipfire'):
        self.config = config
        self.dest_dir = 'ipfire'

    def emit_dns(self):
        dns_name = self._get_dns_entries(self.config)
        dns_entries = []

        for name, ip in dns_name.items():
            dns_entries.append('on,%s,%s,%s' % (ip, name, self.config['dns']['domain']))

        self._write_file(self.dest_dir, 'dns.txt', '\n'.join(dns_entries))

    def emit_dhcp(self):
        clients = self._get_dhcp_entries(self.config)
        leases = []
        for client in clients:
            leases.append('%(mac)s,%(prefix)s%(ip)s,%(enabled)s,,,,%(remark)s' % client)
                
        self._write_file(self.dest_dir, 'dhcp.txt', ('\n'.join(leases)))

    def upload_files(self):
        #env.host_string = "root@192.168.9.1:222"
        fwvars = self.config['firewall']
        env.host_string = "%s@%s:%s" % (fwvars['username'], fwvars['ip'], fwvars['port'])
        with cd('/var/ipfire'), lcd(self.dest_dir):
            put('dhcp.txt', 'dhcp/fixleases')
            put('dns.txt', 'main/hosts')

        url = 'https://%s:444/cgi-bin/dhcp.cgi' % fwvars['ip']
        
        print ("Calling firewall dhcp update on web interface")
        br = mechanize.Browser()
        br.add_password(url, fwvars['webusername'], fwvars['webpassword'])
        br.open(url)
        br.select_form(nr=0)
        br.submit()

        print ("Calling firewall dns update using rebuildhosts")
        run('/usr/local/bin/rebuildhosts')
