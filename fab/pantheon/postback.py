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

def get_job_data():
    results = dict([(k.lower(), v) for k, v in os.environ.iteritems()])
    results['build_status'] = get_build_status(results.get('job_name'), results.get('build_number'))
    return results

def get_build_status(job, id):
    try:
        req = urllib2.Request('http://localhost:8090/job/%s/%s/api/python?tree=result' % (job, id))
        return eval(urllib2.urlopen(req).read()).get('result').lower()
    except urllib2.URLError:
        return "unknown"

def get_data_from_keys(data, keys):
    return dict([(k, v) for k, v in data.iteritems() if k in keys])

def read_workspace_data()
    # change to hudson workspace for current job/build.
    # read file
    # convert to dict
    # return.

def _send_response(responsedict):
    """POST data to Prometheus.
    responsedict: fully formed dict of response data.

    """
    host = 'jobs.getpantheon.com'
    certificate = '/etc/pantheon/system.pem'
    tube = 'atlas-in'
    headers = {'Content-Type': 'application/json'}

    connection = httplib.HTTPSConnection(host,
                                         key_file = certificate,
                                         cert_file = certificate)
    connection.request('POST', '/%s/' % tube, json.dumps(responsedict), headers)
    response = connection.getresponse()
    return response


