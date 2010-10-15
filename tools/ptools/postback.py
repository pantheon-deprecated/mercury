import httplib
import json
import urllib2
import uuid

import gittools

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


def postback_gitstatus(project, head=None):
    """Send Atlas the git status with job_name='git_status' parameter.
    project: project name.
    head: Optional. Last dev commit hash. If coming from git post-recieve-hook,
                    head is known. Otherwise, it will be detected.

    """
    repo = gittools.GitRepo(project)
    status = repo.get_update_status(head)
    postback({'status':status,'job_name':'git_status'})


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

