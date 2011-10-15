# Set up some vars to use.

try:
    API_HOST = open("/opt/api_host.txt").read().strip()
except IOError:
    API_HOST = "api.getpantheon.com"

try:
    API_PORT = open("/opt/api_port.txt").read().strip()
except IOError:
    API_PORT = 8443

try:
    MERCURY_BRANCH = open("/opt/branch.txt").read().strip()
except IOError:
    MERCURY_BRANCH = "master"

try:
    VM_CERTIFICATE =  open("/opt/vm_certificate.txt").read().strip()
except IOError:
    VM_CERTIFICATE = "/etc/pantheon/system.pem"
