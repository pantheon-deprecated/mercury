import cPickle
import httplib
import json
import os
import sys
import urllib2
import uuid
import hudsontools

from fabric.api import local

import pantheon

def postback(cargo, command='atlas'):
    """Send data back to Atlas.
    cargo: dict of data to send.
    task_id: uuid of requesting job.
    command: Prometheus command.

    """
    try:
        task_id = cargo.get('build_parameters').get('task_id')
    except Exception:
        task_id = None

    return _send_response({'id': str(uuid.uuid4()),
                           'command':command,
                           'method':'POST',
                           'response': cargo,
                           'response_to': {'task_id': task_id}})

def get_job_and_id():
    """Return the job name and build number.
    These are set (and retrieved) as environmental variables during Hudson jobs.

    """
    return (os.environ.get('JOB_NAME'), os.environ.get('BUILD_NUMBER'))

def get_build_info(job_name, build_number, check_previous):
    """Return a dictionary of Hudson build information.
    job_name: hudson job name.
    build_number: hudson build number.
    check_previous: bool. If we should return data only if there is a change in
                          build status.

    """
    data = _get_hudson_data(job_name, build_number)

    # If we care, determine if status changed from previous run.
    if check_previous and not _status_changed(job_name, data):
        return None

    # Either we dont care if status changed, or there were changes.
    return {'job_name': job_name,
            'build_number': build_number,
            'build_status': data.get('result'),
            'build_parameters': _get_build_parameters(data)}

def get_build_data():
    """ Return a dict of build data, messages, warnings, errors.

    """
    data = dict()
    data['build_messages'] = list()
    data['build_warnings'] = list()
    data['build_error'] = ''

    build_data_path = os.path.join(hudsontools.get_workspace(), 'build_data.txt')
    if os.path.isfile(build_data_path):
        with open(build_data_path, 'r') as f:
            while True:
                try:
                    # Read a single item from the file, and get response type.
                    var = cPickle.load(f)
                    response_type = var.keys()[0]
                    # If it is a message, add to list of messages.
                    if response_type == 'build_message':
                        data['build_messages'].append(var.get('build_message'))
                    # If it is a warning, add to list of warnings.
                    elif response_type == 'build_warning':
                        data['build_warnings'].append(var.get('build_warning'))
                    # Can only have one error (fatal). 
                    elif response_type == 'build_error':
                        data['build_error'] = var.get('build_error')
                    # General build data. Update data dict.
                    else:
                        data.update(var)
                except (EOFError, ImportError, IndexError):
                    break
    return data

def write_build_data(response_type, data):
    """ Write pickled data to workspace for hudson job_name.

    response_type: The type of response data (generally a job name). May not
               be the same as the initiating hudson job (multiple responses).
    data: Info to be written to file for later retrieval in Atlas postback.

    """
    build_data_path = os.path.join(hudsontools.get_workspace(), 'build_data.txt')

    with open(build_data_path, 'a') as f:
        cPickle.dump({response_type:data}, f)

def build_message(message):
    """Writes messages to file that will be sent back to Atlas,
    message: string. Message to send back to Atlas/user.

    """
    write_build_data('build_message', message)

def build_warning(message):
    """Writes warning to file that will be parsed at the end of a build.
    data: string. Warning message to be written to build_data file.

    Warnings will cause the Hudson build to be marked as unstable.

    """
    write_build_data('build_warning', message)

def build_error(message):
    """Writes error message to file. Sets build as unstable. Exists Job.
    message: string. Error message that will be written to build_data file.

    """
    write_build_data('build_error', message)
    print "\nEncountered a build error. Error message:"
    print message + '\n\n'
    sys.exit(0)

def _status_changed(job_name, data):
    """Returns True if the build status changed from the previous run.
    Will also return true if there is no previous status.
    job_name: hudson job name.
    data: dict from hudsons python api for the current build.

    """
    prev_build_number = int(data.get('number')) - 1
    # Valid previous build exists.
    if prev_build_number > 0:
        result = data.get('result')
        prev_result = _get_hudson_data(job_name, prev_build_number).get('result')
        return result != prev_result
    else:
        # First run, status has changed from "none" to something.
        return True

def _get_build_parameters(data):
    """Return the build parameters from Hudson build API data.

    """
    ret = dict()
    parameters = data.get('actions')[0].get('parameters')
    try:
      for param in parameters:
          ret[param['name']] = param['value']
    except Exception:
      print "WARNING: No build parameters found.";

    return ret

def _get_hudson_data(job, build_id):
    """Return API data for a Hudson build.

    """
    try:
        req = urllib2.Request('http://localhost:8090/job/%s/%s/api/python' % (
                                                               job, build_id))
        return eval(urllib2.urlopen(req).read())
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

