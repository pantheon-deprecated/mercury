import cPickle
import httplib
import json
import os
import urllib2
import uuid

from fabric.api import local

def postback(cargo, task_id=None, command='atlas'):
    """Send data back to Atlas.
    cargo: dict of data to send.
    command: Prometheus command.
    uuid: uuid of requesting job.

    """

    return _send_response({'uuid': uuid.uuid4().hex,
                           'command':command,
                           'method':'POST',
                           'response': cargo,
                           'response_to': {'task_id':task_id}})

def get_job_and_id():
    """Return the job name and build number.
    These are set (and retrieved) as environmental variables during Hudson jobs.

    """
    return (os.environ.get('JOB_NAME'), os.environ.get('BUILD_NUMBER'))

def get_workspace():
    return '/etc/pantheon/hudson/workspace'

def get_build_info(job_name, build_number):
    """Return a dictionary of Hudson build information.

    """
    data = _get_hudson_data(job_name, build_number)

    return {'job_name': job_name,
            'build_number': build_number,
            'build_status': data.get('result'),
            'build_parameters': _get_build_parameters(data)}

def get_build_data(job_name):
    """ Return a dict of build data.
    The data is read from the build_data.txt file created during a Hudson job.

    """
    data = dict()
    build_data_path = os.path.join(get_workspace(), 'build_data.txt')
    if os.path.isfile(build_data_path):
        with open(build_data_path, 'r') as f:
            while True:
                try:
                    data.update(cPickle.load(f))
                except (EOFError, ImportError, IndexError):
                    break
        local('rm -f %s' % build_data_path)
    return {'build_data': data}

def write_build_data(response_type, data):
    """ Write pickled data to workspace for hudson job_name.

    job_name: Hudson job name. Data will be stored in this workspace.
    response_type: The type of response data (generally a job name). May not
               be the same as the initiating hudson job (multiple responses).
    data: dict to be written to file for later retrieval in Atlas postback.

    """
    response = dict()
    response[response_type] = data
    build_data_path = os.path.join(get_workspace(),'build_data.txt')

    with open(build_data_path, 'a') as f:
        cPickle.dump(response, f)

def _get_build_parameters(data):
    """Return the build parameters from Hudson build API data.

    """
    ret = dict()
    parameters = data.get('actions')[0].get('parameters')
    for param in parameters:
        ret[param['name']] = param['value']
    return ret

def _get_hudson_data(job, build_id):
    """Return API data for a Hudson build.

    """
    try:
        req = urllib2.Request('http://localhost:8090/job/%s/%s/api/python' % (
                                                               job, build_id))
        return eval(urllib2.urlopen(req).read())
        #return eval(urllib2.urlopen(req).read()).get('result').lower()
    except urllib2.URLError:
        return None

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

    connection.request('POST', '/%s/' % celery,
                       json.dumps(responsedict),
                       headers)

    response = connection.getresponse()
    return response


