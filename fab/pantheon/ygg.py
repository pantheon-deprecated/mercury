import httplib
import json

host = 'api.getpantheon.com'
port = 8443
certificate = '/etc/pantheon/system.pem'

def get_service(service='', site='self'):
    """ Get service information.
    service: string. Service to query. An empty string returns all services.
    site: string. The UUID of the site to query. Self by default
    
    return: json response from api

    """
    path='/sites/%s/services/%s' % (site, service)
    return _api_request('GET', path)

def set_service(service, data, site='self'):
    """ Update service indicator.
    service: string. Service to query. An empty string returns all services.
    status: dict. Contains data to store
    site: string. The UUID of the site to query. Self by default
    
    return: json response from api

    """
    path='/sites/%s/services/%s' % (site, service)
    return _api_request('PUT', path, data)

def _api_request(method, path, data = None):
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
