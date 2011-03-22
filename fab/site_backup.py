import traceback

from pantheon import backup
from pantheon import jenkinstools

def backup_site(archive_name, project='pantheon', taskid=None):
    archive = backup.PantheonBackup(archive_name, project, taskid)
    archive.backup_files()
    archive.backup_data()
    archive.backup_repo()
    archive.backup_config(version=0)
    archive.finalize()

def remove_backup(archive, taskid=None):
    backup.remove(archive, taskid)

