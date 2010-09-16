from fabric.api import env
from configure import *
from initialization import *
from site_backup import *
from site_import import *
from site_install import *
from site_restore import *
from update import *
env.hosts = ['pantheon@localhost']
