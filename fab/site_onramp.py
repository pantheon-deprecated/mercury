import traceback

from pantheon import onramp
from pantheon import pantheon
from pantheon import restore
from pantheon import status
from pantheon import jenkinstools

def onramp_site(project='pantheon', url=None, profile=None, **kw):
    """Create a new Drupal installation.
    project: Installation namespace.
    profile: The installation type (e.g. pantheon/openatrium)
    **kw: Optional dictionary of values to process on installation.

    """

    archive = onramp.download(url)
    location = onramp.extract(archive)
    handler = _get_handler(profile, project, location)

    try:
        handler.build(location)
    except:
        jenkinstools.junit_error(traceback.format_exc(), 'OnrampSite')
        raise
    else:
        jenkinstools.junit_pass('', 'OnrampSite')

def _get_handler(profile, project, location):
    """Return instantiated profile object.
    profile: name of the installation profile.

    To define additional profile handlers:
        1. Create a new profile class (example below)
        2. Add profile & class name to profiles dict in _get_profile_handler().

    """
    profiles = {'import': _ImportProfile,
                'restore': _RestoreProfile}

    if profile not in profiles.keys():
        profile = onramp.get_onramp_profile(location)

    return profiles[profile](project)


class _ImportProfile(onramp.ImportTools):
    """Generic Pantheon Import Profile.

    """
    def build(self, location):

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
        self.setup_pantheon_modules()
        self.setup_pantheon_libraries()

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

