import argparse
import config
import gerrit

DEFAULT_CONFIG = {
    'gerrit': {
        'host': 'localhost',
        'port': 29418,
        'username': 'SomeUser',
        'key_filename': None,
        'timeout': 10,
        'repo-dir': '/opt/tmp-all-projects',
        'was-here-indicator': '### Setup by gerrit-setup ###'
    }
}


def get_args():
    parser = argparse.ArgumentParser(
        description='Setup initial gerrit users, groups, and All-Projects'
    )
    parser.add_argument('yaml_file', type=str, help="Path to yaml file")
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = get_args()
    _config = config.load_config(args.yaml_file, default=DEFAULT_CONFIG)

    ssh = gerrit.SSH(
        _config['gerrit']['host'],
        _config['gerrit']['port'],
        _config['gerrit']['timeout'],
        _config['gerrit']['username'],
        _config['gerrit']['key_filename']
    )

    groups = _config.get('groups', [])
    for group_data in groups:
        group = gerrit.Group(group_data)
        group.present(ssh)

    users = _config.get('users', [])
    for user_data in users:
        user = gerrit.User(user_data)
        user.present(ssh)

    groups = gerrit.get_groups(ssh)
    gerrit.setup_all_projects(_config, groups)
