
from plugin import Plugin
from fabric.api import env, run, cd, lcd, put
import os
import requests
import mechanize
class Ipfire(Plugin):
    """
        Currently implements:

        * DHCP fixed leases
        * DNS static hosts for fixed leases and aliases

    """

    def __init__ (self, config, dest_dir='ipfire'):
        self.config = config
        self.dest_dir = dest_dir

    def emit_dns(self):
        dns_name = self._get_dns_entries(self.config)
        dns_entries = []

        for name, ip in dns_name.items():
            dns_entries.append('on,%s,%s,%s' % (ip, name, self.config['dns']['domain']))

        self._write_file(self.dest_dir, 'dns.txt', '\n'.join(dns_entries))

    def emit_dhcp(self):
        clients = self._get_dhcp_entries(self.config)
        for interface in clients:
            leases = []
            for client in clients[interface]:
                leases.append('%(mac)s,%(prefix)s%(ip)s,on,,,,%(remark)s' % client)
                    
            self._write_file(self.dest_dir, 'dhcp_%s.txt' % interface, ('\n'.join(leases)))

    def emit_portfw(self):
        rules = self._get_portfw(self.config)

        # Check to make sure each destination is present
        dns_names = self._get_dns_entries(self.config)
        for rule in rules:
            if not rule['dest'] in dns_names:
                print("WARNING: Port forwarding rule %s -> %s:%s is not a valid host" % (rule['port'], rule['dest'], rule['dest_port']))

        my_rules = []
        for i, rule in enumerate(rules):
            rule['ip'] = dns_names[rule['dest']]
            rule['i'] = i+2
            my_rules.append('%(i)s,0,%(type)s,%(port)s,%(ip)s,%(dest_port)s,on,0.0.0.0,%(src)s,%(dest)s' % rule)
        self._write_file(self.dest_dir, 'port_fw.txt', ('\n'.join(my_rules)))


    def upload_files(self):
        #env.host_string = "root@192.168.9.1:222"
        fwvars = self.config['firewall']
        env.host_string = "%s@%s:%s" % (fwvars['username'], fwvars['ip'], fwvars['port'])
        with cd('/var/ipfire'), lcd(self.dest_dir):
            put('dhcp_green.txt', 'dhcp/fixleases')
            put('dns.txt', 'main/hosts')
            put('port_fw.txt', 'portfw/config')

        url = 'https://%s:444/cgi-bin/dhcp.cgi' % fwvars['ip']
        
        print ("Calling firewall dhcp update on web interface")
        br = mechanize.Browser()
        br.add_password(url, fwvars['webusername'], fwvars['webpassword'])
        br.open(url)
        br.select_form(nr=0)
        br.submit()

        print ("Calling firewall dns update using rebuildhosts")
        run('/usr/local/bin/rebuildhosts')

        print ("Calling portfw update using setportfw")
        run('/usr/local/bin/setportfw')
