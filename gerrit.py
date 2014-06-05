import os
import paramiko
import re
import shutil
import StringIO
import subprocess
from pipes import quote


class SSH(object):
    """
    Class for connecting to a gerrit service via ssh and paramiko.

    """
    def __init__(self, host, port, timeout, username, key_filename):
        """
        Inits the SSH object.

        @param host - String Location of gerrit service
        @param port - String Port of gerrit service (usually 29418)
        @param timeout - Integer Timeout in seconds
        @param username - String username
        @param key_filename - String or None

        """
        self._ssh_kwargs = {
            'username': username,
            'port': port,
            'timeout': int(timeout)
        }

        if key_filename:
            self._ssh_kwargs['key_filename'] = key_filename

        self._host = host

    def exec_once(self, cmd):
        """
        Executes a command once

        @param cmd - String command to execute.
        @return Two tuple comprised of the return code and stdout if
            the return code is 0. Returns the stderr if the retcode
            is non zero

        """
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(self._host, **(self._ssh_kwargs))
        _, stdout, stderr = client.exec_command(cmd)

        retcode = stdout.channel.recv_exit_status()
        stream = stdout if not retcode else stderr
        # lines = [line for line in stream.readlines()]
        lines = stream.read()
        client.close()
        return retcode, lines


class Group(object):
    """
    Class that provides some simple accessor methods to a dictionary
    representing a group in Gerrit. Also provides some methods to check
    the existence of a group or to create a new group.

    """
    def __init__(self, data):
        """
        Sets the data for the group and checks to ensure a name is present."

        @param data - Dictionary containing group data

        """
        if 'name' not in data:
            raise Exception('Groups must have a name.')
        self._data = data

    @property
    def description(self):
        """
        Returns the group description or None.

        @return String|None

        """
        return self._data.get('description', None)

    @property
    def name(self):
        """
        Returns the name or None.

        @return String|None

        """
        return self._data.get('name', None)

    @property
    def uuid(self):
        """
        Returns the uuid of this group or None.

        @returns String|None

        """
        return self._data.get('uuid', None)

    @property
    def owner(self):
        """
        Returns the owning group or None.

        @return String|None

        """
        return self._data.get('owner', None)

    @property
    def owner_uuid(self):
        """
        Returns the owning group's uuid or None

        @return String|None
        """
        return self._data.get('owner-uuid',  None)

    def get_ls(self):
        """
        Returns the gerrit command to get details of this group.

        @return String

        """
        return 'gerrit ls-groups -q %s --verbose' % quote(self.name)

    def get_create(self):
        """
        Returns the gerrit command to create this group.

        @return String

        """
        # Description is optional
        description = ''
        if self.description:
            description = ' --description %s' % quote(self.description)

        # Owning group is optional(will default to administrators)
        owner = ''
        if self.owner:
            owner = ' --owner %s' % quote(self.owner)

        # Name is not optional
        return 'gerrit create-group %s%s%s' % (
            quote(self.name),
            description,
            owner
        )

    def exists(self, ssh):
        """
        Executes a 'gerrit ls-groups -q <groupname> --verbose' command.

        @param ssh - SSH object
        @return Boolean True for exists, False for does not exist.

        """
        retcode, __ = ssh.exec_once(self.get_ls())
        return True if not retcode else False

    def present(self, ssh):
        """
        Makes sure this group is present on gerrit. First checks to see
        if this group exists. If it does not exist already, then this method
        will attempt to create it.

        @param ssh - SSH object
        @return True if the group exists or was created, False otherwise.

        """
        # If the group already exists, do nothing.
        if self.exists(ssh):
            print "Group '%s' already exists." % self.name
            return

        # Try to create the group
        retcode, __ = ssh.exec_once(self.get_create())
        if not retcode:
            print "Created group '%s'" % self.name
        return True if not retcode else False


class User(object):
    """
    Class that models an internal user. Provides some simple accessor methods
    to access data of a dictionary that represents a Gerrit user.

    """

    def __init__(self, data):
        """
        Inits the model.

        @param data - Dictionary containing gerrit user data.

        """
        if 'username' not in data:
            raise Exception('Users must have a name.')
        self._data = data

    @property
    def username(self):
        """
        Returns the username or None

        @return String|None

        """
        return self._data.get('username', None)

    @property
    def ssh_key(self):
        """
        Returns the ssh key or None

        @returns String|None

        """
        return self._data.get('ssh-key', None)

    @property
    def groups(self):
        """
        Returns a list of groups or the empty list.

        @returns List

        """
        return self._data.get('groups', [])

    @property
    def full_name(self):
        """
        Returns the full name or None

        @returns String|None

        """
        return self._data.get('full-name', None)

    @property
    def email(self):
        """
        Returns the email or None

        @return String|None

        """
        return self._data.get('email', None)

    @property
    def http_password(self):
        """
        Returns the http password or None.

        @return String|None
        """
    def get_create(self):
        """
        Returns the gerrit command to create this account.

        @returns String

        """
        ssh_key = ''
        if self.ssh_key:
            ssh_key = ' --ssh-key %s' % quote(self.ssh_key)

        groups = ''
        if self.groups:
            groups = ['--group %s' % quote(g) for g in self.groups]
            groups = ' '.join(groups)
            groups = ' %s' % groups

        full_name = ''
        if self.full_name:
            full_name = ' --full-name %s' % quote(self.full_name)

        email = ''
        if self.email:
            email = ' --email %s' % quote(self.email)

        http_password = ''
        if self.http_password:
            http_password = ' --http-password %s' % quote(self.http_password)

        return "gerrit create-account %s%s%s%s%s %s" % (
            ssh_key,
            groups,
            full_name,
            email,
            http_password,
            quote(self.username)
        )

    def present(self, ssh):
        """
        Attempts to create this user. If the return code of that operation
        is 0 then this method returns True. If the return code of that
        operation is 1 and 'already exists' is in the output, then this
        method returns true. Returns false otherwise.

        @param ssh = Gerrit.SSH object
        @returns Boolean True for created or already exists. False otherwise.

        """
        retcode, out = ssh.exec_once(self.get_create())
        if not retcode:
            print "Created user %s" % self.username
            return True
        if retcode == 1 and 'already exists' in out:
            print "User %s already exists" % self.username
            return True
        print "Unable to create user %s:%s" % (self.username, out)
        return False


def get_groups(ssh):
    """
    Executes a gerrit ls-groups --verbose command and parses output
    into groups. Returns a list of groups.

    @param ssh - gerrit.SSH object
    @reurns list

    """
    cmd = 'gerrit ls-groups --verbose'
    groups = []

    # Need a retcode of 0 for success
    retcode, out = ssh.exec_once(cmd)
    if retcode != 0:
        print "Unable to retrieve list of groups."
        return groups

    # Send to buffer to easy read one line at a time
    _buffer = StringIO.StringIO()
    _buffer.write(out)
    _buffer.seek(0)

    # Parse each line into a group object and append to list
    for line in _buffer.readlines():
        tokens = re.split(r'\t+', line)
        group_data = {
            'name': tokens[0],
            'uuid': tokens[1],
            'description': None if len(tokens) == 5 else tokens[2],
            'owner': tokens[2] if len(tokens) == 5 else tokens[3],
            'owner-uuid': tokens[3] if len(tokens) == 5 else tokens[4]
        }
        groups.append(Group(group_data))

    # Return the final list.
    return groups


def groups_file_contents(groups, indicator=""):
    _buffer = StringIO.StringIO()
    if len(indicator) > 0:
        _buffer.write(indicator)
        _buffer.write("\n")
    for g in groups:
        _buffer.write("%s\t%s\n" % (g.uuid, g.name))
    return _buffer.getvalue()


def project_config_contents(source_file, indicator=""):
    _buffer = StringIO.StringIO()
    if len(indicator) > 0:
        _buffer.write(indicator)
        _buffer.write("\n")
    with open(source_file, 'r') as f:
        _buffer.write(f.read())
    return _buffer.getvalue()


def file_contains(_file, indicator):
    with open(_file, 'r') as f:
        contents = f.read()
    return indicator in contents


def setup_all_projects(config, groups):

    print "Attempting to intialize All-Projects config"

    repo_dir = os.path.expanduser(config['gerrit']['repo-dir'])
    repo_dir = os.path.abspath(repo_dir)

    # Make Empty directory - We want this to stop and fail on OSError
    print "Creating directory %s" % repo_dir
    os.makedirs(repo_dir)

    # Save the current working directory
    old_cwd = os.getcwd()

    indicator = config['gerrit']['was-here-indicator']

    try:
        # Change cwd to that repo
        os.chdir(repo_dir)

        # Git init empty directory
        print "Initting git directory."
        args = ['git', 'init']
        subprocess.check_call(args)

        # Add remote origin
        ssh_url = 'ssh://%s@%s:%s/All-Projects' % (
            config['gerrit']['username'],
            config['gerrit']['host'],
            config['gerrit']['port']
        )
        print "Adding remote %s" % ssh_url
        args = ['git', 'remote', 'add', 'origin', ssh_url]
        print ' '.join(args)
        subprocess.check_call(args)

        # Fetch refs/meta/config for all-project
        print "Fetching refs/meta/config"
        args = ['git', 'fetch', 'origin',
                'refs/meta/config:refs/remotes/origin/meta/config']
        print " ".join(args)
        subprocess.check_call(args)

        # Checkout refs/meta/config
        print "Checking out branch meta/config"
        args = ['git', 'checkout', 'meta/config']
        print " ".join(args)
        subprocess.check_call(args)

        repo_modified = False
        # update groups file
        # Check to see if groups was already touched by this tool.
        _file = os.path.join(repo_dir, 'groups')
        if not file_contains(_file, indicator):
            # Create entire new groups file
            contents = groups_file_contents(groups, indicator)
            with open(_file, 'w') as f:
                f.write(contents)
            print contents
            repo_modified = True

        # Update project.config file
        # Check to see if this file was already touched by this tool.
        _file = os.path.join(repo_dir, 'project.config')
        if not file_contains(_file, indicator):
            # Create the new project.config file
            contents = project_config_contents(
                config['gerrit']['all-projects-config'],
                indicator
            )
            with open(_file, 'w') as f:
                f.write(contents)
            print contents
            repo_modified = True

        if repo_modified:
            args = ['git', 'config', 'user.email', config['gerrit']['git-config-email']]
            subprocess.check_call(args)

            args = ['git', 'config', 'user.name', config['gerrit']['git-config-name']]
            subprocess.check_call(args)

            # Git commit
            args = [
                'git', 'commit', '-a', '-m', 'Setting up All-Projects'
            ]
            print "Committing changes."
            subprocess.check_call(args)

            # Git push
            args = ['git', 'push', 'origin', 'meta/config:refs/meta/config']
            print "Pushing changes."
            subprocess.check_call(args)

        else:
            print "groups and project.config already modified."

    finally:
        # Change to old current working directory
        os.chdir(old_cwd)

        # Attempt to clean up created directory
        shutil.rmtree(repo_dir)
