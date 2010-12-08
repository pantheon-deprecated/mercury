import os

from fabric.api import local

from pantheon import pantheon
from pantheon import postback

def clean_workspace():
    """Cleanup data files from build workspace.

    This should be run before any other processing is done.

    """
    workspace = postback.get_workspace()
    if os.path.exists(workspace):
        local('rm -f %s' % os.path.join(workspace, '*'))

def parse_build_data():
    """Output build messages/warnings/errors to stdout & junit file.

    """
    # Only need JUNIT file if we are in a Hudson build.
    if _in_hudson():
        _write_junit_file()

    messages, warnings, error = _get_build_messages()
    if messages:
        print '\nBuild Messages: \n' + '=' * 30
        print '\n'.join(messages)
    if warnings:
        print '\nBuild Warnings: \n' + '=' * 30
        print '\n'.join(warnings)
    if error:
        print '\nBuild Error: \n' + '=' * 30
        print error

def _write_junit_file():
    """Creates a junit xml file from build warnings and build errors.

    """
    messages, warnings, error = _get_build_messages()
    report_data = dict()

    if error:
        report_data['type'] = 'Error'
        report_data['message'] = '<error>%s</error>' % error
    elif warnings:
        report_data['type'] = 'Warning'
        report_data['message'] = '<error>%s</error>' % '\n'.join(warnings)
    else:
        report_data['type'] = 'None'
        report_data['message'] = ''

    template = pantheon.build_template(
                        pantheon.get_template('junit.xml'),
                        report_data)

    with open(os.path.join(postback.get_workspace(),'warnings.xml'), 'w') as f:
        f.write(template)

def _get_build_messages():
    """Return the build messages/warnings/errors.
    """
    data = postback.get_build_data()
    return (data.get('build_messages'),
            data.get('build_warnings'),
            data.get('build_error'))

def _in_hudson():
    """If inside a Hudson build, return True.

    """
    # If the 'BUILD_TAG' environment var exists, assume we are in Hudson.
    return bool(os.environ.get('BUILD_TAG'))

