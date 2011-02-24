# vim: tabstop=4 shiftwidth=4 softtabstop=4
import httplib
import json
import random
import re
import ssl
import string
import sys
import urllib2
from urlparse import urlparse

def config_request(method = "GET", data = None, url = 'https://configrepo.getpantheon.com:8443/sites/self'):
    """Utility function for communicating with the configrepo.

    """
    certificate = '/etc/pantheon/system.pem'
    parsed = urlparse(url)
    port = parsed.port
    if parsed.port is None:
       port = 8443

    try:
        connection = httplib.HTTPSConnection(
            parsed.netloc.partition(':')[0],
            port,
            key_file = certificate,
            cert_file = certificate
        )

        connection.request(method, parsed.path, data)
        complete_response = connection.getresponse()
        if (complete_response.status == 404):
            return None
        if (complete_response.status == 403):
            return False
        response = complete_response.read()

    except httplib.HTTPException as detail:
        raise 'HTTP Error: %s' % detail

    except ssl.SSLError as detail:
        if detail.errno == 8:
            # Error number 8 should be "EOF occurred in violation of protocol" meaning networking
            raise 'SSL EOF: %s' % detail
        else:
            raise 'Unexpected SSL Error: %s' % detail

    return response