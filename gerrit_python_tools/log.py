import config
import logging
import logging.handlers
import os

DEFAULT_CONFIG = {
    'file': '/var/log/gerrit-python-tools/gerrit-sync',
    'level': 'info',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
}


def init_logdir(logfile):
    """
    Creates the directories needed for logfile if they do not exist.

    @param logfile - String log file name/path

    """
    logdir, _ = os.path.split(logfile)
    if not os.path.exists(logdir):
        os.makedirs(logdir)


def get_logger(name='gerrit-python-tools'):
    """
    Returns a logger for logging.

    @param name - String name of the logger. gerrit-python-tools by default.
    @returns - logger

    """
    return logging.getLogger(name)

logging_conf_file = '/etc/gerrit-python-tools/logging.yaml'
logging_conf = config.load_config(logging_conf_file, default=DEFAULT_CONFIG)

# Get log path/file from config
logfile = logging_conf['file']
init_logdir(logfile)

# Get log level from config
loglevel = logging_conf['level']
loglevel = getattr(logging, loglevel.upper())

# Create log format from config
logformat = logging_conf['format']
logformatter = logging.Formatter(logformat)

# Create log handler
loghandler = logging.handlers.TimedRotatingFileHandler(
    logfile,
    when="midnight"
)
loghandler.setFormatter(logformatter)

# Set level and handler to root logger
logger = logging.getLogger()
logger.addHandler(loghandler)
logger.setLevel(loglevel)
