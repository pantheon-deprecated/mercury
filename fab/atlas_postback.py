import os
import sys
import urllib2

from pantheon import postback
from pantheon import gittools

from fabric.api import *

def postback_general():
    # Gets all environmental variables, and the hudson job status.
    data = postback.get_job_data()
    # The keys for the data we want to send back.
    keys = ['build_status', 'job_name', 'build_number', 'project']
    response = get_data_from_keys(data, keys)

    postback.postback(response, data.get('uuid'))

def postback_gitstatus(project):
    """Send Atlas the git status with job_name='git_status' parameter.
    project: project name.

    """
    repo = gittools.GitRepo(project)
    status = repo.get_update_status()
    postback.postback({'status':status,'job_name':'git_status'})

def postback_core_update():
    # Gets all environmental variables, and the hudson job status.
    data = postback.get_job_data()
    # The keys for the data we want to send back.
    keys = ['build_status', 'job_name', 'build_number', 'project', 'keep']
    response = get_data_from_keys(data, keys)

    #TODO: function below doesn't exist yet. It will read data from hudson workspace
    # into a dict, then we can update our response dict with the extra info.
    response.update(postback.read_workspace_data())

    postback.postback(response, data.get('uuid'))

def postback_drupal_status():
    #The change here will be similar. The 'work' of the job (running drush) will
    #write data to a file in the workspace. This will pick up that data and send it back.

    #This way, if the 'work' fails (permissions errors, for example), we will still report back to atlas.
    pass
