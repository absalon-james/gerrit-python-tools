import time
import config
import gerrit
import log
import logging


DEFAULT_CONFIG = {
    'gerrit': {
        'host': 'localhost',
        'port': 29418,
        'username': 'SomeUser',
        'key_filename': None,
        'timeout': 10,
        'was-here-indicator': '### Setup by gerrit-sync ###'
    }
}

logger = log.get_logger()


def get_ssh(_config):
    """
    Creates a gerrit.SSH object from a dictionary of parameters.

    @param _config - Dictionary with the key 'gerrit' and a value
        of a dictionary with host, port, timeout, username, and
        key_filename keys.
    @return gerrit.SSH

    """
    gerrit_config = _config['gerrit']
    return gerrit.SSH(
        gerrit_config['host'],
        gerrit_config['port'],
        gerrit_config['timeout'],
        gerrit_config['username'],
        gerrit_config['key_filename']
    )


def sync_groups(_config):
    """
    Ensures groups listed described by _config are present. Will create them
    if they DO NOT exist but will leave them alone if they DO exist.

    @param _config - Dictionary
  
    """
    ssh = get_ssh(_config)
    for group_data in _config.get('groups', []):        
        group = gerrit.Group(group_data)        
        group.present(ssh)
        print ""


def sync_users(_config):
    """
    Ensures users desribed by _config are present. Will create them if they
    DO NOT exist but will leave them alone if they DO exist.

    @param _config - Dictionary

    """
    ssh = get_ssh(_config)
    for user_data in _config.get('users', []):
        user = gerrit.User(user_data)
        user.present(ssh)
        print ""


def sync_projects(_config, specific=None):
    """
    Syncs projects described in _config. Projects that are to be synced
    have a source repo. Syncing is the process of pushing those changes
    to downstream. Optionally, a specific project can be named and only
    that project will be synced.

    @param _config - Dictionary
    @param specific - String name of a specific project.

    """
    ssh = get_ssh(_config)

    # Get list of groups for building groups file
    groups = gerrit.get_groups(ssh)

    # Convert project dictionaries to Project objects
    projects = [gerrit.Project(p) for p in _config.get('projects', [])]

    # If a specific project is provided, filter out other projects
    if specific:
        projects = [p for p in projects if p.name == specific]
        if not projects:
            msg = "Project %s: Not in configuration" % specific
            logger.error(msg)
            print msg

    for p in projects:
        p.ensure(ssh, _config['gerrit'], groups)
        print ""


def sync(yaml_file=None, groups=True, users=True, projects=True, project=None):
    """
    Main sync entry point. Orchestrates the syncing of users, groups, and
    projects as described by a yaml file.

    @param yaml_file - String location of a yaml file.
    @param groups - Boolean Groups will be synced if true.
    @param users - Boolean Users will be synced if true.
    @param projects - Boolean Projects will be synced if true.
    @param project - String specific project to sync.

    """
    try:
        if yaml_file is None:
            yaml_file = '/etc/gerrit-python-tools/projects.yaml'
        _config = config.load_config(yaml_file, default=DEFAULT_CONFIG)

        logger = log.get_logger()
        start = time.time()

        logger.info("gerrit-sync starting...")

        if groups:
            sync_groups(_config)

        if users:
            sync_users(_config)

        if projects:
            sync_projects(_config, specific=project)

        duration = time.time() - start
        msg = "gerrit-sync run finished in %s seconds." % duration
        logger.info(msg)
        print msg
    except Exception as e:
        logging.exception("Error occurred:")
        raise e
