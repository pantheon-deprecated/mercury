import os

def deploy():
    """Install pre-req packages and fabric, then run fab initialize.

    """
    packages = ['python-configobj',
                'python-dev',
                'python-m2crypto',
                'python-mysqldb',
                'python-paramiko',
                'python-pip',
                'python-crypto',
                'python-setuptools',
                'python-lxml']

    os.system('apt-get install -y %s' % ' '.join(packages))
    os.system('pip install fabric==0.9.3')
    os.system('cd /opt/pantheon/fab && fab initialize')

if __name__ == '__main__':
    deploy()

