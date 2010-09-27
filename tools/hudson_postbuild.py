import json
import os
import httplib
import urllib2
import uuid


def get_build_status(job, id):
    try:
        req = urllib2.Request('http://localhost:8090/job/%s/%s/api/python?tree=result' % (job, id))
        return eval(urllib2.urlopen(req).read()).get('result').lower()
    except urllib2.URLError:
        return "unknown"

if __name__ == '__main__':

    host = 'jobs.getpantheon.com'
    certificate = '/etc/pantheon/system.pem'
    # TODO: Use a new, response-only tube.
    tube = 'rest-in'

    results = dict([(k.lower(), v) for k, v in os.environ.iteritems()])
    results['build_status'] = get_build_status(results.get('job_name'), results.get('build_number'))

    response_keys = ['build_status', 'job_name', 'build_number','project', 'environment']
    responsebody = dict([(k, v) for k, v in results.iteritems() if k in response_keys])

    responsedict = {'uuid': uuid.uuid4().hex,
                    'command': 'request',
                    'method': 'POST',
                    'url': results['callback_url'],
                    'body': {'response': responsebody, 'response_to': {'uuid': results['uuid']}},
                   }

    # TODO: Use a "with" block for the connection?
    connection = httplib.HTTPSConnection(
	host,
	key_file = certificate,
	cert_file = certificate
    )
    connection.putrequest('POST', '/%s/' % tube)
    connection.endheaders()
    connection.send(json.dumps(responsedict))
    response = connection.getresponse()
