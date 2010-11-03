import update
from pantheon import install

def install_site(project='pantheon', profile='pantheon', **kw):
    """ Create a new Drupal installation.
    project: Installation namespace.
    profile: The installation type (e.g. pantheon/openatrium)
    **kw: Optional dictionary of values to process on installation.

    """
    data = {'profile':profile,
            'project':project}

    data.update(kw)

    handler = _get_profile_handler(**data)
    handler.build(**data)

class _PantheonProfile(install.InstallTools):
    """ Default Pantheon Installation Profile.

    """
    def build(self, **kw):

        # Create a new project
        self.build_project_branch()

        # Build project in a temporary directory
        self.build_working_dir()
        self.build_project_modules()  #NOTE: temporary until integrated with repo
        self.build_project_libraries()#NOTE: temporary until integrated with repo
        self.build_file_dirs()
        self.build_settings_file()

        # Push changes from working directory to central repo
        self.push_to_repo()

        # Clone project to all environments
        self.setup_environments()

        # Build non-code site features.
        self.setup_database()
        self.setup_solr_index()
        self.setup_vhost()
        self.setup_drupal_cron()
        self.setup_drush_alias()
        self.setup_permissions()

        update.git_repo_status(self.project)

        self.cleanup()
        self.server.restart_services()


"""
To define additional profile handlers:
   1. Create a new profile class
   2. Add profile name and class to profiles dict in _get_profiles_handler().
"""

def _get_profile_handler(profile, **kw):
    """ Return instantiated profile object.
        profile: name of the installation profile.

    """
    profiles = {'pantheon': _PantheonProfile}

    # If profile: doesn't exist, use 'pantheon'
    return profiles.has_key(profile) and \
           profiles[profile](**kw) or \
           profiles['pantheon'](**kw)

