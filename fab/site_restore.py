from pantheon import onramp
from pantheon import restore

def restore_site(project, url):
    restorer = restore.RestoreTools(project)
    archive = onramp.download(url)

    restorer.extract_backup(archive)
    restorer.parse_backup()
    restorer.restore_database()

