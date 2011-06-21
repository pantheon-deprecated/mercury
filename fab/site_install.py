from pantheon import install
from pantheon import status
from pantheon import logger

def install_site(project='pantheon', version=6, profile='pantheon'):
    """ Create a new Pantheon Drupal installation.

    """
    data = {'profile': profile,
            'project': project,
            'version': int(version)}

    _installer(**data)

def install_project(url=None, profile='gitsource'):
    """ Create a new Installation from a git source.

    """
    data = {'url': url,
            'profile': profile}

    _installer(**data)

def _installer(**kw):
    #TODO: Move logging into pantheon libraries for better coverage.
    log = logger.logging.getLogger('pantheon.install.site')
    log = logger.logging.LoggerAdapter(log, kw)
    log.info('Site installation of project %s initiated.' % kw.get('project'))
    try:
        installer = install.InstallTools(**kw)

        # Remove existing project.
        installer.remove_project()

        # Create a new project
        if kw['profile'] == 'pantheon':
            installer.setup_project_repo()
            installer.setup_project_branch()
            installer.setup_working_dir()
        elif kw['profile'] == 'makefile':
            installer.process_makefile(kw['url'])
        elif kw['profile'] == 'gitsource':
            installer.process_gitsource(kw['url'])

        # Run bcfg2 project bundle.
        installer.bcfg2_project()

        # Setup project
        installer.setup_database()
        installer.setup_files_dir()
        installer.setup_settings_file()

        # Push changes from working directory to central repo
        installer.push_to_repo()

        # Build non-code site features.
        installer.setup_solr_index()
        installer.setup_drupal_cron()
        installer.setup_drush_alias()

        # Clone project to all environments
        installer.setup_environments()

        # Cleanup and restart services
        installer.cleanup()
        installer.server.restart_services()

        # Send back repo status.
        status.git_repo_status(installer.project)
        status.drupal_update_status(installer.project)

        # Set permissions on project
        installer.setup_permissions()

    except:
        log.exception('Site installation was unsuccessful')
        raise
    else:
        log.info('Site installation successful')

