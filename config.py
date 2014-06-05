import yaml


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
        default = {}

    # Copy the default config
    config = default

    # Read in yaml config file
    with open(filename, 'r') as f:
        diff = yaml.load(f)

    # Update config
    config = merge_dict(config, diff)
    return config
