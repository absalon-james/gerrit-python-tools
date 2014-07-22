import config
import gerrit
import log
import signal
import time
import thread
import sync
import upstream


logger = log.get_logger()


def pull_downstream(conf, stream, pool, schedule, yaml_file):
    """
    Pulls an event from the queue on downstream.
    Filters and assigns tasks to handle this event.
    Does nothing if there is no event.

    @param conf - Dictionary
    @param stream - gerrit.SSHStream object
    @param pool - thread.WorkerPool
    @param schedule - List of (time, tasks) tuples. Use to schedule
        events later.
    @param yaml_file - Location of configuration file
    @return Boolean - True if event was process, False Otherwise

    """
    event = stream.get_event()
    # Look for comment added type events
    if event and event.get('type') == 'comment-added':
        if conf['daemon']['upstream']:
            args = [yaml_file, event]
            kwargs = {}
            pool.add_task(upstream.send_upstream, *args, **kwargs)
    return event is not None


def pull_upstream(_config, stream, pool, schedule, yaml_file):
    """
    Pulls an event from the queue on upstream.
    Filters and assigns tasks to handle this event.
    Does nothing if there is no event.

    @param conf - Dictionary
    @param stream - gerrit.SSHStream object
    @param pool - thread.WorkerPool
    @param schedule - List of (time, tasks) tuples. Use to schedule
        events later.
    @param yaml_file - Location of configuration file
    @return Boolean - True if event was process, False Otherwise

    """
    delay = int(_config['daemon']['delay'])
    event = stream.get_event()
    if event and event.get('type') == 'ref-updated':
        if _config['daemon']['sync']:
            name = event['refUpdate']['project']
            t = time.time() + delay
            args = []
            kwargs = {
                'yaml_file': yaml_file,
                'users': False,
                'groups': False,
                'project': name
            }
            schedule.append((t, sync.sync, args, kwargs))

    return event is not None


def service(yaml_file):
    """
    Initializes a downstream event listener, an upstream event listener,
    and a threadpool to handle events from both. Also sets up a schdule
    if things need to be delayed.

    Runs in infinite loop until killed.
    Each loop iteration consists of checking the schedule, checking
    downstream, then checking upstream. Sleep if no action taken.

    @param yaml_file - String location to configuration

    """
    # Get configuraion
    _config = config.load_config(yaml_file)

    numthreads = int(_config['daemon']['numthreads'])
    sleep = int(_config['daemon']['sleep'])

    # Register the signal handler to kill threads
    signal.signal(signal.SIGINT, thread.stop_threads)
    signal.signal(signal.SIGTERM, thread.stop_threads)

    schedule = list()
    pool = thread.WorkerPool(numthreads)

    downstream_remote = gerrit.Remote(_config['gerrit'])
    downstream = downstream_remote.SSHStream()
    downstream.start()

    upstream_remote = gerrit.Remote(_config['upstream'])
    upstream = upstream_remote.SSHStream()
    upstream.start()

    while True:
        downstream_active = False
        upstream_active = False

        # Check schedule and add events to event pool
        if len(schedule) > 0 and time.time() > schedule[0][0]:
            t, func, args, kwargs = schedule.pop(0)
            pool.add_task(func, *args, **kwargs)
            continue

        # Check for new events
        downstream_active = pull_downstream(_config, downstream,
                                            pool, schedule, yaml_file)
        upstream_active = pull_upstream(_config, upstream,
                                        pool, schedule, yaml_file)

        if downstream_active:
            logger.debug("Downstream is active")
        if upstream_active:
            logger.debug("Upstream is active")
        logger.debug("Schedule len: %s" % len(schedule))

        # Sleep if no events recieved.
        if not downstream_active and not upstream_active:
            time.sleep(sleep)
            continue
