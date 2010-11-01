import httplib
import json
import urllib2
import uuid

def postback(cargo, request_uuid=None, command='atlas'):
    """Send data back to Atlas.
    cargo: dict of data to send.
    command: Prometheus command.
    uuid: uuid of requesting job.

    """

    return _send_response({'uuid': uuid.uuid4().hex,
                           'command':command,
                           'method':'POST',
                           'response': cargo,
                           'response_to': {'uuid':request_uuid}})

def _send_response(responsedict):
    """POST data to Prometheus.
    responsedict: fully formed dict of response data.

    """
    host = 'jobs.getpantheon.com'
    certificate = '/etc/pantheon/system.pem'
    celery = 'atlas.notify'
    headers = {'Content-Type': 'application/json'}

    connection = httplib.HTTPSConnection(host,
                                         key_file = certificate,
                                         cert_file = certificate)
    connection.request('POST', '/%s/' % celery, json.dumps(responsedict), headers)
    response = connection.getresponse()
    return response

