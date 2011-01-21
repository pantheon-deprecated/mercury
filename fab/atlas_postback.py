import os

from pantheon import postback
from optparse import OptionParser

def main():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage, description="Send information about a Hudson job (and resulting data) back to Atlas.")
    parser.add_option('-c', '--check_changed_status', dest="check_changed_status", action="store_true", default=False, help='Postback only if the status of the build has changed from the previous run.')
    parser.add_option('-s', '--suppress', dest="suppress", action="store_true", default=False, help='Suppress postback on unstable builds.')
    (options, args) = parser.parse_args()
    postback_atlas(options.check_changed_status, options.suppress)

def postback_atlas(check_changed_status=False, suppress=False):
    """ Send information about a Hudson job (and resulting data) back to Atlas.
    check_changed_status: bool. If we want to only return data if the status of
                                the build has changed from the previous run.

    This should only be called from within a Hudson Post-Build Action.

    """
    # Get job_name and build_number.
    job_name, build_number = postback.get_job_and_id()

    # Get build info: job_name, build_number, build_status, build_parameters.
    response = postback.get_build_info(job_name,
                                       build_number,
                                       check_changed_status)

    # If there is data we want to send back.
    if response:
        # Get build data from build actions (in hudson workspace).
        response.update({'build_data': postback.get_build_data()})

        # Send response to Atlas.
	if suppress and (response['build_status'] == 'UNSTABLE'):
	    print('Build status is UNSTABLE. No postback performed.')
	else:
            postback.postback(response)
    else:
        print('Build status has not changed. No postback performed.')

if __name__ == '__main__':
    main()
