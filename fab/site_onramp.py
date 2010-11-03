import pantheon

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


class _ImportProfile(pantheon.onramp.ImportTools):

    def build(self, url, **kw):

        # Download, extract, and parse the tarball.
        tarball = project.tools.download(url)
        self.extract(tarball)
        self.parse_archive()

        # Import site and download pantheon modules.
        self.import_database()
        self.import_files()
        self.import_pantheon_modules()

        # Push imported project from working directory to central repo
        self.push_to_repo(tag='import')

        # Clone project to all environments
        self.setup_environments()

        # Build non-code site features
        self.build_solr_index()
        self.build_vhost()
        self.build_drupal_cron()
        self.build_drush_alias()

        # Enable modules & set variables. Then push changes to test/live.
        self.import_drupal_settings()
        self.update_environment_databases()
        self.update_environment_files()
        self.setup_permissions()

        self.cleanup()
        self.server.restart_services()


class _RestoreProfile(pantheon.restore.RestoreTools):

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
    profiles = {'import': _ImportProfile
                'restore': _RestoreProfile}

    # If profile doesn't exist, use 'import'
    return profiles.has_key(profile) and \
           profiles[profile](**kw) or \
           profiles['import'](**kw)


