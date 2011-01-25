import sys

from pantheon import backup
from pantheon import hudsontools

def backup_site(archive_name, project='pantheon'):
    archive = backup.PantheonBackup(archive_name, project)

    try:
        archive.backup_files()
        archive.backup_data()
        archive.backup_repo()
        archive.backup_config(version=0)
        archive.make_archive()
        archive.move_archive()
        archive.cleanup()
    except:
        hudsontools.junit_error(sys.exc_info()[0], 'BackupSite')
        raise
    else:
        hudsontools.junit_pass('Backup successful.', 'BackupSite')

def remove_backup(archive):
    try:
        backup.remove(archive)
    except:
        hudsontools.junit_error(sys.exc_info()[0], 'RemoveBackup')
        raise
    else:
        hudsontools.junit_pass('Removal successful.', 'RemoveBackup')

