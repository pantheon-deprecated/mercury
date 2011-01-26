import os

from fabric.api import local

from pantheon import pantheon
from pantheon import postback
from pantheon import hudsontools

def clean_workspace():
    """Cleanup data files from build workspace.

    This should be run before any other processing is done.

    """
    workspace = hudsontools.get_workspace()
    if os.path.exists(workspace):
        local('rm -f %s' % os.path.join(workspace, '*'))

def parse_build_data():
    """Output build messages/warnings/errors to stdout.

    """
    messages, warnings, errors = _get_build_messages()

    # Output messages to console to ease debugging.
    if messages:
        messages = '\n'.join(messages)
        print('\nBuild Messages: \n' + '=' * 30)
        print(messages)
    if warnings:
        warnings = '\n'.join(warnings)
        print('\nBuild Warnings: \n' + '=' * 30)
        print(warnings)
    if errors:
        print('\nBuild Error: \n' + '=' * 30)
        print(errors)

def _get_build_messages():
    """Return the build messages/warnings/errors.
    """
    data = postback.get_build_data()
    return (data.get('build_messages'),
            data.get('build_warnings'),
            data.get('build_error'))

