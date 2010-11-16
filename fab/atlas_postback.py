import os

from pantheon import postback

def postback_atlas():
    """ Send information about a Hudson job (and resulting data) back to Atlas.

    This should only be called from within a Hudson job.
    Ideally from within a Post-Build Action.

    """
    # Get job_name and build_number.
    job_name, build_number = postback.get_job_and_id()

    # Get build info 
    #     job_name, build_number, build_status, and build_parameters.
    response = postback.get_build_info(job_name, build_number)

    # Get build data 
    #     Data from build actions (in hudson workspace).
    response.update(postback.get_build_data(job_name))

    # Send response to Atlas.
    postback.postback(response)

def clear_postback_workspace():
    """Remove all files in the shared Panthoen workspace.

    """
    workspace = postback.get_workspace()
    if os.path.exists(workspace):
        os.system('rm -f %s' % os.path.join(workspace, '*'))

if __name__ == '__main__':
    postback_atlas()