# vim: tabstop=4 shiftwidth=4 softtabstop=4
import tempfile

from fabric.api import *

from pantheon import backup


def backup_site(archive_name, project='pantheon'):
    archive = backup.PantheonBackup(archive_name, project)

    archive.backup_files()
    archive.backup_data()
    archive.backup_repo()
    archive.make_archive()
    archive.move_archive()
    archive.cleanup()

