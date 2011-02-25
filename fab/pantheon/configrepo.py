import httplib
import json

host = 'api.getpantheon.com'
port = 8443
path = '/sites/self/configuration'
certificate = '/etc/pantheon/system.pem'

def get_config():
    """ Return project configuration dict."""
    connection = httplib.HTTPSConnection(host,
                                         port,
                                         key_file = certificate,
                                         cert_file = certificate)

    connection.request('GET', path)
    response = connection.getresponse()

    if response.status == 404:
        return None
    if response.status == 403:
        return False

    config = json.loads(response.read())
    return config or raise("No configuration data exists")

