from pantheon import backup
from pantheon import logger

def backup_site(archive_name, project='pantheon'):
    log = logger.logging.getLogger('pantheon.site_backup')
    archive = backup.PantheonBackup(archive_name, project)
    log.info('Calculating necessary disk space.')
    if archive.free_space():
        log.info('Sufficient disk space found.')
        archive.backup_files()
        archive.backup_data()
        archive.backup_repo()
        archive.backup_config(version=0)
        archive.finalize()
    else:
        log.error('Insufficient disk space to perform archive.')
        raise IOError('Insufficient disk space to perform archive.')

def remove_backup(archive):
    backup.remove(archive)

