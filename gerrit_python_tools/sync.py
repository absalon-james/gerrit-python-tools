import config
import gerrit
import log
import logging
import time


logger = log.get_logger()


def sync_groups(_config):
    """
    Ensures groups listed described by _config are present. Will create them
    if they DO NOT exist but will leave them alone if they DO exist.

    @param _config - Dictionary

    """
    remote = gerrit.Remote(_config['gerrit'])
    for group_data in _config.get('groups', []):
        group = gerrit.Group(group_data)
        group.present(remote)
        print ""


def sync_users(_config):
    """
    Ensures users desribed by _config are present. Will create them if they
    DO NOT exist but will leave them alone if they DO exist.

    @param _config - Dictionary

    """
    remote = gerrit.Remote(_config['gerrit'])
    for user_data in _config.get('users', []):
        user = gerrit.User(user_data)
        user.present(remote)
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
    remote = gerrit.Remote(_config['gerrit'])

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
        p.ensure(remote, _config)
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
        _config = config.load_config(yaml_file)

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
