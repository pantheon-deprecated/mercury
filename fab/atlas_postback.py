import os

from pantheon import postback

def postback_atlas(ifchanged=False):
    """ Send information about a Hudson job (and resulting data) back to Atlas.

    This should only be called from within a Hudson Post-Build Action.

    """
    # Get job_name and build_number.
    job_name, build_number = postback.get_job_and_id()

    # Get build info 
    #     job_name, build_number, build_status, and build_parameters.
    response = postback.get_build_info(job_name, build_number, ifchanged)
    
    # Check status and exit(0) if we're only into changes
    if (ifchanged && response.changed == True):
        exit(0)

    # Get build data 
    #     Data from build actions (in hudson workspace).
    response.update({'build_data': postback.get_build_data()})

    # Send response to Atlas.
    postback.postback(response)

if __name__ == '__main__':
    postback_atlas()
