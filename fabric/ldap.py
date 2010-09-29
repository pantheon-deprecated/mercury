# vim: tabstop=4 shiftwidth=4 softtabstop=4
from fabric.api import *
from genshi.template import TemplateLoader, TextTemplate

from tempfile import NamedTemporaryFile
import os

loader = TemplateLoader(
    os.path.join(os.path.dirname(__file__), 'templates'),
    auto_reload=True
    )
    
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
            
    local("sudo apt-get install -y debconf-utils")
            
    ldap_auth_conf_template = loader.load('ldap-auth-config.preseed.cfg', cls=TextTemplate)
    ldap_auth_conf = ldap_auth_conf_template.generate(ldap_domain=ldap_domain, server_host=server_host).render()
    with NamedTemporaryFile() as temp_file:
        temp_file.write(ldap_auth_conf)
        temp_file.seek(0)
        local("sudo debconf-set-selections " + temp_file.name)
        
    local("sudo apt-get install -y libnss-ldap ldap-auth-config")
        
    ldap_conf_template = loader.load('ldap.conf', cls=TextTemplate)
    ldap_conf = ldap_conf_template.generate(ldap_domain=ldap_domain, server_host=server_host).render()
    with NamedTemporaryFile() as temp_file:
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

