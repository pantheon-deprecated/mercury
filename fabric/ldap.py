# vim: tabstop=4 shiftwidth=4 softtabstop=4
import os
import string
import tempfile

from fabric.api import *
from pantheon import pantheon

def build_ldap_client(base_domain = "example.com", require_group = None, server_host = "auth.example.com"):
    """ Set permissions on project directory, settings.php, and files dir.
    environments: Optional. List.
    
    """
    if server_host == "auth.example.com":
        server_host = "auth." + base_domain

    # If necessary, restrict by group
    if require_group is not None:
        #local("sudo echo '-:ALL EXCEPT root sudo (" + require_group + "):ALL' | tee -a /etc/security/access.conf")
        local("sudo echo 'AllowGroups root sudo " + require_group + "' | tee -a /etc/ssh/sshd_config")
    else:
        local("sudo echo 'AllowGroups root sudo' | tee -a /etc/ssh/sshd_config")

    local("sudo /etc/init.d/ssh restart")
            
    ldap_domain = _ldap_domain_to_ldap(base_domain)
    values = {'ldap_domain':ldap_domain,'server_host':server_host}
            
    template = '/opt/pantheon/fabric/templates/ldap-auth-config.preseed.cfg'
    ldap_auth_conf = pantheon.build_template(template, values)
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(ldap_auth_conf)
        temp_file.seek(0)
        local("sudo debconf-set-selections " + temp_file.name)
        
    template = '/opt/pantheon/fabric/templates/ldap.conf'
    ldap_conf = pantheon.build_template(template, values)
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(ldap_conf)
        temp_file.seek(0)
        local("sudo cp " + temp_file.name + " /etc/ldap.conf")

    local("sudo auth-client-config -t nss -p lac_ldap")

def _ldap_domain_to_ldap(domain):
    parts = domain.split(".")
    ldap_domain_parts = []
    for part in parts:
        ldap_domain_parts.append("dc=" + part.lower())
    ldap_domain = ",".join(ldap_domain_parts)
    return ldap_domain

