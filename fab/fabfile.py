from fabric.api import env
from atlas_postback import *
from configure import *
from buildtools import *
from initialization import *
from monitoring import *
from permissions import *
from pantheon.status import *
from site_backup import *
from site_onramp import *
from site_install import *
from update import *
env.hosts = ['pantheon@localhost']
