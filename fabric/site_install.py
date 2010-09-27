from pantheon import install
from pantheon import onramp

def install_site(project='pantheon', profile='pantheon', **kw):
    """ Create a new Drupal installation.
    project: Installation namespace.
    profile: The installation type (e.g. pantheon/openatrium)
    **kw: Optional dictionary of values to process on installation.

    """
    data = {'profile':profile,'project':project}
    data.update(kw)

    handler = _get_handler(**data)
    handler.build(**data)


def _get_handler(profile, **kw):
    """ Return instantiated profile object.
        profile: name of the installation profile.

    """
    profiles = {'pantheon':_PantheonProfile,
                'import':_ImportProfile,
                'openatrium':_OpenAtriumProfile,
                'openpublish':_OpenPublishProfile}

    # If handler doesn't exist, use pantheon
    return profiles.has_key(profile) and \
           profiles[profile](**kw) or \
           profiles['pantheon'](**kw)


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

class _PantheonProfile(install.InstallTools):
    """ Default Pantheon Installation Profile.
    
    """

    def __init__(self, project, **kw):
        install.InstallTools.__init__(self, project)
  

    def build(self, **kw):
        
        # Create a new project in /var/git/projects
        self.build_project_branch()

        # Clone project to a working directory
        self.build_working_dir()
        self.build_project_modules()  #NOTE: temporary until integrated with repo
        self.build_project_libraries()#NOTE: temporary until integrated with repo
        self.build_file_dirs()
        self.build_settings_file()
        self.build_gitignore()

        # Push changes from working directory to /var/git/projects
        self.push_to_repo()

        # Clone project to all environments
        self.build_environments()     

        # Finish related (non-code) site building tasks.
        self.build_permissions()
        self.build_database()
        self.build_solr_index()
        self.build_vhost()
        self.build_drupal_cron()
        self.build_drush_alias()

        self.cleanup()
        self.server.restart_services()

class _ImportProfile(onramp.ImportTools):

    def __init__(self, project, **kw):
        onramp.ImportTools.__init__(self, project)

    def build(self, url, **kw):
        tarball = onramp.download(url)

        self.extract(tarball)
        self.parse_archive()

        self.import_database()
        self.import_files()
        self.build_drush_alias()
        self.import_pantheon_modules()

        # Push changes from working directory to /var/git/projects
        self.push_to_repo(tag='import')

        # Clone project to all environments
        self.build_environments(tag='import')

        # Finish related (non-code) site building tasks.
        self.setup_permissions()
        self.build_solr_index()
        self.build_vhost()
        self.build_drupal_cron()
        self.build_drush_alias()

        archive.import_drupal_settings()

        self.cleanup()
        self.server.restart_services()


class _OpenAtriumProfile(install.InstallTools):
    """ Open Atrium Installation Profile.

    """
    def __init__(project, **kw):
        install.InstallTools.__init__(self, project)
  

    def build(self, **kw):
        pass


class _OpenPublishProfile(install.InstallTools):
    """ Open Publish Installation Profile.

    """
    def __init__(project, **kw):
        install.InstallTools.__init__(self, project)
  

    def build(self, **kw):
        pass

