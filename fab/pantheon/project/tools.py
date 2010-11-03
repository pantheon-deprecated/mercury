import os
import tempfile

from fabric.api import local

def download(url):
    """Download url to temporary directory and return path to file.
    url: fully qualified url of file to download.
    returns: full path to downloaded file.

    """
    download_dir = tempfile.mkdtemp()
    filebase = os.path.basename(url)
    filename = os.path.join(download_dir, filebase)

    curl(url, filename)
    return filename

def drush(alias, cmd, option):
    """Use drush to run a command on an aliased site.
    alias: alias name of site (just name, no '@')
    cmd: drush command to run
    option: options / parameters for the command.

    """
    with settings(warn_only=True):
        local('drush -y @%s %s %s' % (alias, cmd, option))

def drush_set_variables(alias, variables = dict()):
    """Set drupal variables using drush.
    php-eval is used because drush vset always sets vars as strings.
    alias: alias name of site (just name, no '@')
    variables: dict of var_name/values.

    """
    for key, value in variables.iteritems():
        # normalize strings and bools
        if isinstance(value, str):
            value = "'%s'" % value
        if isinstance(value, bool):
            if value == True:
                value = 'TRUE'
            elif value == False:
                value = 'FALSE'
        local("drush @%s php-eval \"variable_set('%s',%s);\"" % (alias,
                                                                key,
                                                                value))

def _curl(url, destination):
    """Use curl to save url to destination.
    url: url to download
    destination: full path/ filename to save curl output.

    """
    local('curl "%s" -o "%s"' % (url, destination))

