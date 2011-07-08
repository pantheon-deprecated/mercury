from pantheon import onramp
from pantheon import pantheon
from pantheon import restore
from pantheon import status
from pantheon import logger

def onramp_site(project='pantheon', url=None, profile=None, **kw):
    """Create a new Drupal installation.
    project: Installation namespace.
    profile: The installation type (e.g. pantheon/openatrium)
    **kw: Optional dictionary of values to process on installation.

    """
    #TODO: Move logging into pantheon libraries for better coverage.
    log = logger.logging.getLogger('pantheon.onramp.site')
    log = logger.logging.LoggerAdapter(log,
                                       {"project": project})
    archive = onramp.download(url)
    location = onramp.extract(archive)
    handler = _get_handler(profile, project, location)

    log.info('Initiated site build.')
    try:
        handler.build(location)
    except:
        log.exception('Site build encountered an exception.')
        raise
    else:
        log.info('Site build was successful.')

def _get_handler(profile, project, location):
    """Return instantiated profile object.
    profile: name of the installation profile.

    To define additional profile handlers:
        1. Create a new profile class (example below)
        2. Add profile & class name to profiles dict in _get_profile_handler().

    """
    profiles = {'import': _ImportProfile,
                'restore': _RestoreProfile}

    # If the profile is not pre-defined try to determine if it is a restore
    # or an import (we may not know if they are uploading a pantheon backup or
    # their own existing site). Defaults to 'onramp'.
    if profile not in profiles.keys():
        profile = onramp.get_onramp_profile(location)

    return profiles[profile](project)


class _ImportProfile(onramp.ImportTools):
    """Generic Pantheon Import Profile.

    """
    def build(self, location):

        self.build_location = location
        # Parse the extracted archive.
        self.parse_archive(location)

        # Remove existing project.
        self.remove_project()

        # Create a new project
        self.setup_project_repo()
        self.setup_project_branch()

        # Run bcfg2 project bundle.
        self.bcfg2_project()

         # Import existing site into the project.
        self.setup_database()
        self.import_site_files()
        self.setup_files_dir()
        self.setup_settings_file()

        # Push imported project from working directory to central repo
        self.push_to_repo()

        # Build non-code site features
        self.setup_solr_index()
        self.setup_drupal_cron()
        self.setup_drush_alias()

        # Turn on modules, set variables
        self.enable_pantheon_settings()

        # Clone project to all environments
        self.setup_environments()

        # Set permissions on project.
        self.setup_permissions()

        # Cleanup and restart services.
        self.cleanup()
        self.server.restart_services()

        # Send version and repo status.
        status.git_repo_status(self.project)
        status.drupal_update_status(self.project)


class _RestoreProfile(restore.RestoreTools):
    """Generic Pantheon Restore Profile.

    """
    def build(self, location):

        # Parse the backup.
        self.parse_backup(location)

        # Run bcfg2 project bundle.
        self.bcfg2_project()

        self.setup_database()
        self.restore_site_files()
        self.restore_repository()

        # Build non-code site features
        self.setup_solr_index()
        self.setup_drupal_cron()
        self.setup_drush_alias()

        self.setup_permissions()
        self.server.restart_services()

        # Send version and repo status.
        status.git_repo_status(self.project)
        status.drupal_update_status(self.project)

