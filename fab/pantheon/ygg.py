import httplib
import json

host = 'api.getpantheon.com'
port = 8443
certificate = '/etc/pantheon/system.pem'

# Note: Same call structure as in the Prometheus httprequest module.
# TODO: Unify
def send_event(thread, details, labels=['source-cloud'], site='self', source='cloud'):
    """ Send event.
    thread: string. Aggregates events from the same site together.
    details: dict. Contains data to send
    labels: list. Additional labels for listing the thread the event is in.
    site: string. The UUID of the site to query. Self by default

    return: json response from api

    """
    path='/sites/%s/events/' % (site)

    details = {'source': source, source: details}

    request = {'thread': thread,
               'details': details,
               'labels': labels}
    return _api_request('POST', path, request)

def get_config(site='self'):
    """Return a dictionary of configuration data.
    site: string. The UUID of the site to query. Self by default

    return: json response from api

    """
    path='/sites/%s/configuration' % (site)
    return _api_request('GET', path)

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
    data: dict. Contains data to store
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

    if method == 'PUT' or method == 'POST':
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

    if method == 'PUT' or method == 'POST':
        return True

    return json.loads(response.read())
