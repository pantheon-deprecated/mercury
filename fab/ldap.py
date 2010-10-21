# vim: tabstop=4 shiftwidth=4 softtabstop=4
import os
import string
import tempfile

from fabric.api import *
from pantheon import pantheon

def build_ldap_client(base_domain = "example.com", require_group = None, server_host = None):

    server = pantheon.PantheonServer()

    if not server_host:
        server_host = "auth." + base_domain
            
    ldap_domain = _ldap_domain_to_ldap(base_domain)
    values = {'ldap_domain':ldap_domain,'server_host':server_host}
            
    template = pantheon.get_template('ldap-auth-config.preseed.cfg')
    ldap_auth_conf = pantheon.build_template(template, values)
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(ldap_auth_conf)
        temp_file.seek(0)
        local("sudo debconf-set-selections " + temp_file.name)
        
    # /etc/ldap/ldap.conf    
    template = pantheon.get_template('openldap.ldap.conf')
    openldap_conf = pantheon.build_template(template, values)
    with open('/etc/ldap/ldap.conf', 'w') as f:
        f.write(openldap_conf)

    # /etc/ldap.conf
    template = pantheon.get_template('pam.ldap.conf')
    ldap_conf = pantheon.build_template(template, values)
    with open('/etc/ldap.conf', 'w') as f:
        f.write(ldap_conf)

    # Restrict by group
    allow = ['root', 'sudo']
    if require_group:
        allow.append(require_group)

    with open('/etc/ssh/sshd_config', 'a') as f:
        f.write('\nAllowGroups %s\n' % (' '.join(allow)))
        f.write('UseLPK yes\n')
        f.write('LpkLdapConf /etc/ldap.conf\n')

    local("sudo auth-client-config -t nss -p lac_ldap")

    with open('/etc/sudoers', 'a') as f:
        f.write('%' + '%s ALL=(ALL) ALL' % require_group)

    # Add LDAP user to www-data, and ssl-cert groups.
    local('usermod -aG %s %s' % ('ssl-cert', require_group))

    # Restart after ldap is configured so openssh-lpk doesn't choke.
    local("sudo /etc/init.d/ssh restart")
    
    # Write the group to a file for later reference.
    server.set_ldap_group(require_group)
    
    # Make the git repo and www directories writable by the group
    local("chown -R %s:%s /var/git/projects" % (require_group, require_group))
    local("chmod -R g+w /var/git/projects")

def _ldap_domain_to_ldap(domain):
    return ','.join(['dc=%s' % part.lower() for part in domain.split('.')])
