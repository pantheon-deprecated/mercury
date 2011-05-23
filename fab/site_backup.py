from pantheon import backup

def backup_site(archive_name, project='pantheon'):
    archive = backup.PantheonBackup(archive_name, project)
    if archive.free_space():
        archive.backup_files()
        archive.backup_data()
        archive.backup_repo()
        archive.backup_config(version=0)
        archive.finalize()
    else:
        raise IOError('Insufficient disk space to perform backup.')

def remove_backup(archive):
    backup.remove(archive)

