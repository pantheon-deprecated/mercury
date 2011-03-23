from pantheon import backup

DESTINATION = '/srv/dev_downloads'

def get_dev_downloads(resource, project, user=None):
    """Wapper method for a Jenkins job to get development resources.
    resource: type of download you want (all/files/data/code/drushrc)
    project: project name
    server_name: getpantheon server name.
    user: user that has ssh access to box.

    """
    archive_name = 'local_dev_%s' % resource
    resource_handler = {'all': _dev_all,
                        'files': _dev_files,
                        'data': _dev_data,
                        'code': _dev_code,
                        'drushrc': _dev_drushrc}
    resource_handler[resource](archive_name, project, user)

def _dev_all(archive_name, project, user):
    archive = backup.PantheonBackup(archive_name, project)

    # Only create archive of development environment data.
    archive.get_dev_files()
    archive.get_dev_data()
    archive.get_dev_code(user)
    archive.get_dev_drushrc(user)

    # Create the tarball and move to final location.
    archive.finalize(_get_destination())

def _dev_files(archive_name, project, *args):
    archive = backup.PantheonBackup(archive_name, project)
    archive.get_dev_files()
    archive.finalize(_get_destination())

def _dev_data(archive_name, project, *args):
    archive = backup.PantheonBackup(archive_name, project)
    archive.get_dev_data()
    archive.finalize(_get_destination())

def _dev_code(archive_name, project, user):
    archive = backup.PantheonBackup(archive_name, project)
    archive.get_dev_code(user)
    archive.finalize(_get_destination())

def _dev_drushrc(archive_name, project, user):
    archive = backup.PantheonBackup(archive_name, project)
    archive.get_dev_drushrc(user)
    archive.finalize(_get_destination())

def _get_destination():
    return DESTINATION

