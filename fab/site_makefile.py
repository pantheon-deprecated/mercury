from pantheon import install
from pantheon import status
from pantheon import logger

#TODO: Move logging into pantheon libraries for better coverage.
def install_makefile(project='pantheon', makefile_url=None, profile='default'):
    """ Create a new Drupal installation from a drush makefile.

    """
    data = {'project': project,
            'makefile_url': makefile_url,
            'profile': profile}

    log = logger.logging.getLogger('pantheon.install.makefile')
    log = logger.logging.LoggerAdapter(log, data)
    log.info('Makefile installation of %s initiated.' % project)

    try:
        handler = _get_profile_handler(**data)
        handler.build(**data)
    except:
        log.exception('Site installation was unsuccessful')
        raise
    else:
        log.info('Site installation successful')

def _get_profile_handler(profile, **kw):
    """ Return instantiated profile object.
        profile: name of the installation profile.

    """
    profiles = {'default': _DefaultProfile}

    # If the selected profile doesn't exist, use the default.
    return profiles.has_key(profile) and \
           profiles[profile](**kw) or \
           profiles['default'](**kw)

class _DefaultProfile(install.InstallTools):
    """ Default makefile installation profile.

    """
    def build(self, makefile_url, **kw):

        # Remove existing project.
        self.remove_project()

        # Create a new project
        self.setup_project_repo()
        self.process_makefile(makefile_url)

        # Run bcfg2 project bundle.
        self.bcfg2_project()

        # Setup project
        self.setup_database()
        self.setup_files_dir()
        self.setup_settings_file()
        self.setup_pantheon_modules()
        self.setup_pantheon_libraries()

        # Push changes from working directory to central repo
        self.push_to_repo()

        # Build non-code site features.
        self.setup_solr_index()
        self.setup_drupal_cron()
        self.setup_drush_alias()

        # Clone project to all environments
        self.setup_environments()

        # Cleanup and restart services
        self.cleanup()
        self.server.restart_services()

        # Send back repo status.
        status.git_repo_status(self.project)
        status.drupal_update_status(self.project)

        # Set permissions on project
        self.setup_permissions()

