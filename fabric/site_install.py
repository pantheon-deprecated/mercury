from pantheon import install
import pdb

def install_site(project='pantheon', profile='pantheon'):
    """ Create a new Drupal installation.
    project: Installation namespace.
    profile: The installation type (e.g. pantheon/openatrium)

    """
    #If additional values are needed in the installation profile classes,
    #they can be placed in init_dict or build_dict and will be passed to
    #the profile object (and ignored by existing profile classes).
    init_dict = {'profile':profile,
                 'project':project}

    build_dict = {}

    handler = _get_handler(**init_dict)
    handler.build(**build_dict)


def _get_handler(profile, **kw):
    """ Return instantiated profile object.
        profile: name of the installation profile.

    """
    profiles = {'pantheon':_PantheonProfile,
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
        makefile = '/opt/pantheon/fabric/templates/pantheon.make'
        
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
        pdb.set_trace()
        self.build_permissions()
        self.build_database()
        self.build_solr_index()
        self.build_vhost()
        self.build_drupal_cron()

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

