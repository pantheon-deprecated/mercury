from pantheon import siteinstall
import pdb

def install_site(project='pantheon', profile='pantheon'):
    """ Create a new Drupal installation.
    project: Installation namespace.
    profile: The installation type (e.g. pantheon/openatrium)

    """
    pdb.set_trace()
    #If additional values are needed in the installation profile classes,
    #they can be placed in init_dict or build_dict and will be passed to
    #the profile object (and ignored by existing profile classes).
    init_dict = {'profile':profile,
                 'project':project}

    build_dict = {}

    handler = get_handler(**init_dict)
    handler.build(**build_dict)


def get_handler(profile, **kw):
    """ Return instantiated profile object.
        profile: name of the installation profile.

    """
    profiles = {'pantheon':PantheonProfile,
                'openatrium':OpenAtriumProfile,
                'openpublish':OpenPublishProfile,}

    return profiles.has_key(profile) and \
           profiles[profile](**kw) or \
           profiles['PantheonProfile'](**kw)


"""Additional profile handlers can be defined by:
     1. Create a new profile class (example below)
     2. Add the profile name & class name to the profiles dict in get_handler()

class MIRProfile(siteinstall.InstallTools):
    def __init__(self, project, **kw):
        siteinstall.InstallTools.__init__(self, project, **kw)

    def build(self, **kw):
        # Step 1: create a working installation
        # Step 2: ??? 
        # Step 3: Make it rain.

"""

class PantheonProfile(siteinstall.InstallTools):
    """ Default Pantheon Installation Profile
    
    """

    def __init__(self, project, **kw):
        siteinstall.InstallTools.__init__(self, project, **kw)
  

    def build(self, **kw):
        makefile = '/opt/pantheon/fabric/templates/pantheon.make'

        self.build_makefile(makefile)
        self.build_file_dirs()
        self.build_gitignore()
        self.build_settings_file()
        self.build_database()
        self.server.create_solr_index(self.project)
        self.server.create_vhost(self.project)
        self.server.create_drupal_cron(self.project)


class OpenAtriumProfile(siteinstall.InstallTools):
    """ Open Atrium Installation Profile

    """
    def __init__(project, **kw):
        siteinstall.InstallTools.__init__(self, project, **kw)
  

    def build(self, **kw):
        pass


class OpenPublishProfile(siteinstall.InstallTools):
    """ Open Publish Installation Profile

    """
    def __init__(project, **kw):
        siteinstall.InstallTools.__init__(self, project, **kw)
  

    def build(self, **kw):
        pass
