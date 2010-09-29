from pantheon import onramp

def import_site(project='pantheon', profile='pantheon', url=None, **kw):
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


def _get_profile_handler(profile, **kw):
    """ Return instantiated profile object.
        profile: name of the installation profile.

    """
    profiles = {'import': _ImportProfile}

    # If profile doesn't exist, use 'import'
    return profiles.has_key(profile) and \
           profiles[profile](**kw) or \
           profiles['import'](**kw)


"""
To define additional profile handlers:
     1. Create a new profile class (example below)
     2. Add the profile name & class name to the profiles dict in get_handler().
     Example profile handler:

class MIRProfile(install.InstallTools):
    def __init__(self, project, **kw):
        install.InstallTools.__init__(self, project)

    def build(self, **kw):
        # Step 1: create a working installation
        # Step 2: ??? 
        # Step 3: Make it rain.
"""


class _ImportProfile(onramp.ImportTools):


    def __init__(self, project, **kw):
        """Initialize onramp.ImportTools - inherits install.InstallTools"""
        onramp.ImportTools.__init__(self, project)


    def build(self, url, **kw):

        # Download, extract, and parse the tarball.
        tarball = onramp.download(url)
        self.extract(tarball)
        self.parse_archive()

        # Import site and download pantheon modules.
        self.import_database()
        self.import_files()
        self.import_pantheon_modules()

        # Push imported project from working directory to central repo
        self.push_to_repo(tag='import')

        # Clone project to all environments
        self.build_environments(tag='import')

        # Build non-code site features
        self.setup_permissions()
        self.build_solr_index()
        self.build_vhost()
        self.build_drupal_cron()
        self.build_drush_alias()

        # Enable modules & set variables. Then push changes to test/live.
        self.import_drupal_settings()
        self.update_environment_databases()

        self.cleanup()
        self.server.restart_services()
