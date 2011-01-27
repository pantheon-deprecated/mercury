import traceback

from pantheon import onramp
from pantheon import pantheon
from pantheon import restore
from pantheon import status
from pantheon import hudsontools

def onramp_site(project='pantheon', profile=None, url=None, **kw):
    """Create a new Drupal installation.
    project: Installation namespace.
    profile: The installation type (e.g. pantheon/openatrium)
    **kw: Optional dictionary of values to process on installation.

    """
    
    data = {'profile': profile,
            'project': project,
            'url': url}

    data.update(kw)

    handler = _get_profile_handler(**data)
    try:
        handler.build(**data)
    except:
        hudsontools.junit_error(traceback.format_exc(), 'OnrampSite')
        raise
    else:
        hudsontools.junit_pass('', 'OnrampSite')
        

def _get_profile_handler(profile, **kw):
    """Return instantiated profile object.
    profile: name of the installation profile.

    To define additional profile handlers:
        1. Create a new profile class (example below)
        2. Add profile & class name to profiles dict in _get_profile_handler().

    """
    profiles = {'import': _ImportProfile,
                'restore': _RestoreProfile}

    # If profile doesn't exist, use 'import'
    return profiles.has_key(profile) and \
           profiles[profile](**kw) or \
           profiles['import'](**kw)


class _ImportProfile(onramp.ImportTools):
    """Generic Pantheon Import Profile.

    """
    def build(self, url, **kw):

        # Download, extract, and parse the tarball.
        tarball = self.download(url)
        self.extract(tarball)
        self.parse_archive()

        # Remove existing project.
        self.remove_project()

        # Create a new project
        self.setup_project_repo()
        self.setup_project_branch()

        # Import existing site into the project.
        self.setup_database()
        self.import_site_files()
        self.setup_files_dir()
        self.setup_settings_file()
        self.setup_pantheon_modules()
        self.setup_pantheon_libraries()

        # Push imported project from working directory to central repo
        self.push_to_repo()

        # Build non-code site features
        self.setup_solr_index()
        self.setup_vhost()
        self.setup_phpmyadmin()
        self.setup_drupal_cron()
        self.setup_drush_alias()

        # Turn on modules, set variables
        self.enable_pantheon_settings()

        # Clone project to all environments
        self.setup_environments()

        # Set permissions on project.
        self.setup_permissions()

        # Cleanup and restart services.
        self.cleanup(tarball)
        self.server.restart_services()

        # Send version and repo status.
        status.git_repo_status(self.project)
        status.drupal_update_status(self.project)


class _RestoreProfile(restore.RestoreTools):
    """Generic Pantheon Restore Profile.

    """
    def build(self, url, **kw):

        #Download, extract, and parse the backup.
        backup = pantheon.download(url)
        self.extract(backup)
        self.parse_backup()

        self.setup_database()
        self.restore_site_files()
        self.restore_repository()

        # Build non-code site features
        self.setup_solr_index()
        self.setup_vhost()
        self.setup_drupal_cron()
        self.setup_drush_alias()

        self.setup_permissions()
        self.server.restart_services()

        # Send version and repo status.
        status.git_repo_status(self.project)
        status.drupal_update_status(self.project)

