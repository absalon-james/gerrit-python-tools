import config
import gerrit
import log
import logging
import signal
import time
import thread


DEFAULT_CONFIG = {
    'gerrit': {
        'host': 'localhost',
        'port': 29418,
        'username': 'SomeUser',
        'key_filename': None,
        'timeout': 10,
        'was-here-indicator': '### Setup by gerrit-sync ###'
    },
    'upstream': {
        'host': '',
        'port': 29418,
        'username': 'SomeUser',
        'key_filename': None,
        'timeout': 10,
        'keepalive': 60
    },
    'daemon': {
        'numthreads': 5,
        'sleep': 5,
        'delay': 60 * 2
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


def get_ssh_stream(_config):
    """
    Creates a gerrit.SSHStream object from a dictionary of parameters.

    @param _config - Dictionary with the key 'upstream' and a value of
        a dictionary with host, port, timeout, username, key_filename, and
        keepalive keys.
    @return gerrit.SSHStream

    """
    upstream_config = _config['upstream']
    return gerrit.SSHStream(
        upstream_config['host'],
        upstream_config['port'],
        upstream_config['timeout'],
        upstream_config['username'],
        upstream_config['key_filename'],
        upstream_config['keepalive']
    )


def get_config(yaml_file):
    """
    Returns a dictionary created by parsing a yaml file.

    @param yaml_file - String yaml file location
    @returns - Dictionary

    """
    if yaml_file is None:
        yaml_file = '/etc/gerrit-python-tools/projects.yaml'
    return config.load_config(yaml_file, default=DEFAULT_CONFIG)


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
        _config = get_config(yaml_file)

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


def sync_daemon(yaml_file=None):
    """
    Not really a daemon. More of a long running loop that you would run
    inside of a daemon. Let upstart/init scripts run this as a background
    process.

    I would use the same queue for the event stream and the worker pool,
    but it became necessary to introduce a delay from the time an upstream
    event is triggered to the time action is taken.

    @param yaml_file - Configuration file to read.

    """
    # Get configuraion
    _config = get_config(yaml_file)

    numthreads = int(_config['daemon']['numthreads'])
    sleep = int(_config['daemon']['sleep'])
    delay = int(_config['daemon']['delay'])

    # Register the signal handler to kill threads
    signal.signal(signal.SIGINT, thread.stop_threads)
    signal.signal(signal.SIGTERM, thread.stop_threads)

    schedule = list()

    pool = thread.WorkerPool(numthreads)

    # Start listening to upstream gerrit
    stream = get_ssh_stream(_config)
    stream.start()

    while True:
        # Check schedule and add events to event pool
        if len(schedule) > 0 and time.time() > schedule[0][0]:
            t, func, args, kwargs = schedule.pop(0)
            pool.add_task(func, *args, **kwargs)

        # Check for new events from the stream
        event = stream.get_event()
        if not event:
            time.sleep(sleep)
            continue

        # Do some filtering on event type and then add delay. When syncing,
        # upstream gerrit may not have replicated to github at the time of
        # the event reporting.
        if event.get('type') == 'ref-updated':
            name = event['refUpdate']['project']
            t = time.time() + delay
            args = []
            kwargs = {
                'yaml_file': yaml_file,
                'users': False,
                'groups': False,
                'project': name
            }
            schedule.append((t, sync, args, kwargs))
