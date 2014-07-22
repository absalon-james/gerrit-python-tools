import yaml


def get_default_projects_config():
    """
    Returns the default configuration.
    @TODO - Maybe make this static and use the copy module
        when grabbing the config?

    @return - Dictionary

    """
    return {
        'git-config': {
            'email': '',
            'name': ''
        },
        'gerrit': {
            'host': 'localhost',
            'port': 29418,
            'username': 'SomeUser',
            'key_filename': None,
            'timeout': 10,
            'keepalive': 60,
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
            'delay': 60 * 2,
            'upstream': True,
            'sync': True
        }
    }


def merge_dict(a, b):
    """
    Update dictionary a with b. Should be recursive. The goal is to
    recurively update a default configuration with the user provided
    configuration. The values in b should "win".
    Based on example at:
        https://www.xormedia.com/recursively-merge-dictionaries-in-python/

    @param a - Dict a
    @param b - Value or dict b
    @return Updated a or value b if b is not a dict.

    """
    if not isinstance(b, dict):
        return b

    for key, value in b.iteritems():
        if key in a and isinstance(a[key], dict):
            a[key] = merge_dict(a[key], value)
        else:
            a[key] = value
    return a


def load_config(filename, default=None):
    """
    Reads a yaml file located at filename.
    Updates the default configuration with information from
    the yaml file. Returns a dictionary

    @param filename - String filename
    @param default - Dictionary, default configuration
    @return dict

    """
    if default is None:
        default = get_default_projects_config()

    # Copy the default config
    config = default

    # Read in yaml config file
    with open(filename, 'r') as f:
        diff = yaml.load(f)

    # Update config
    config = merge_dict(config, diff)
    return config
