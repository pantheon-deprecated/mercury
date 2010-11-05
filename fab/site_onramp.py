from pantheon import onramp
from pantheon import restore
from pantheon import project

def import_site(project='pantheon', profile=None, url=None, **kw):
    """ Create a new Drupal installation.
    project: Installation namespace.
    profile: The installation type (e.g. pantheon/openatrium)
    **kw: Optional dictionary of values to process on installation.

    """
    data = {'profile': profile,
            'project': project,
            'url': url}

    data.update(kw)

    handler = _get_profile_handler(**data)
    handler.build(**data)


class _ImportProfile(onramp.ImportTools):

    def build(self, url, **kw):

        # Download, extract, and parse the tarball.
        tarball = project.tools.download(url)
        self.extract(tarball)
        self.parse_archive()

        # Create a new project
        self.setup_project_repo()
        self.setup_project_branch()
        self.setup_working_dir()

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
        self.setup_drupal_cron()
        self.setup_drush_alias()

        # Turn on modules, set variables
        self.enable_pantheon_settings()

        # Clone project to all environments
        self.setup_environments()

        # Set permissions on project.
        self.setup_permissions()

        #TODO: respond to atlast with gitsatus

        # Cleanup and restart services.
        self.cleanup()
        self.server.restart_services()


class _RestoreProfile(restore.RestoreTools):

    def build(self, url, **kw):

        #Download, extract, and parse the backup.
        backup = project.tools.download(url)
        self.extract(archive)
        self.parse_backup()

        self.restore_database()
        self.restore_files()


"""
To define additional profile handlers:
    1. Create a new profile class (example below)
    2. Add profile & class name to profiles dict in _get_profile_handler().

"""

def _get_profile_handler(profile, **kw):
    """ Return instantiated profile object.
        profile: name of the installation profile.

    """
    profiles = {'import': _ImportProfile,
                'restore': _RestoreProfile}

    # If profile doesn't exist, use 'import'
    return profiles.has_key(profile) and \
           profiles[profile](**kw) or \
           profiles['import'](**kw)


