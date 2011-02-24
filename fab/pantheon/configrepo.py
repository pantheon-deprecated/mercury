import httplib
import json

host = 'api.getpantheon.com'
port = 8443
path = '/sites/self/configuration'
certificate = '/etc/pantheon/system.pem'

def get_config():
    """Return a dictionary of configuration data."""
    return _config_request('GET')

def update_config(data):
    """Push updates to the config repo.
    data: dict of data to update on the config repo.

    """
    return _config_request('PUT', data)

def _config_request(method, data = None):
    """Make GET or PUT request to config server.
    Returns dict of response data.

    """
    headers = {}

    if method == 'PUT':
        headers = {'Content-Type': 'application/json'}
        data = json.dumps(data)

    connection = httplib.HTTPSConnection(host,
                                         port,
                                         key_file = certificate,
                                         cert_file = certificate)

    connection.request(method, path, data, headers)
    response = connection.getresponse()

    if response.status == 404:
        return None
    if response.status == 403:
        return False

    if method == 'PUT':
        return True

    return json.loads(complete_response.read())

