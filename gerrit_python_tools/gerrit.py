import git
import log
import logging
import os
import paramiko
import re
import shutil
import StringIO
from uuid import uuid4
from pipes import quote

# Turn down the logging output of paramiko
log.get_logger('paramiko').setLevel(logging.ERROR)

# Get a logger
logger = log.get_logger()


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
        port = int(port)
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
        logger.debug("Executing: %s" % cmd)
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(self._host, **(self._ssh_kwargs))
        _, stdout, stderr = client.exec_command(cmd)

        retcode = stdout.channel.recv_exit_status()
        stream = stdout if not retcode else stderr
        output = stream.read()
        client.close()
        logger.debug(output)
        return retcode, output


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
        msg = "Group %s: Ensuring present." % self.name
        logger.info(msg)
        print msg

        # If the group already exists, do nothing.
        if self.exists(ssh):
            msg = "Group %s: Already exists." % self.name
            logger.info(msg)
            print msg
            return

        # Try to create the group
        retcode, __ = ssh.exec_once(self.get_create())
        if not retcode:
            msg = "Group %s: Created" % self.name
            logger.info(msg)
            print msg
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
k
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
        msg = "User %s: Ensuring present." % self.username
        logger.info(msg)
        print msg

        retcode, out = ssh.exec_once(self.get_create())
        if not retcode:
            msg = "User %s: Created." % self.username
            logger.info(msg)
            print msg
            return True
        if retcode == 1 and 'already exists' in out:
            msg = "User %s: Already exists." % self.username
            logger.info(msg)
            print msg
            return True

        msg = "User %s: Unable to create - %s" % (self.username, out)
        log.error(msg)
        print msg
        return False


class Project(object):
    """
    Models a gerrit project

    """

    def __init__(self, data):
        """
        Inits the project from a dictionary

        @param data - Dictionary describing the gerrit project
        """
        if 'name' not in data:
            raise Exception("Projects must have a name")
        self._data = data

    @property
    def name(self):
        """
        Returns the project's name

        @returns String

        """
        return self._data.get('name')

    @property
    def create(self):
        """
        Returns Boolean indicating whether or not to create
        the project.

        @return Boolean

        """
        return self._data.get('create', False)

    @property
    def config(self):
        """
        Returns the location of the project configuration
        file.

        @returns String|None

        """
        return self._data.get('config', None)

    @property
    def source(self):
        """
        Returns the source for this project if creating
        from another repo. Should be a git url.

        @returns String|None

        """
        return self._data.get('source', None)

    @property
    def preserve_prefix(self):
        """
        Returns the prefix for branches that should be preserved and
        not deleted.

        @returns String|None
        """
        return self._data.get('preserve_prefix', None)

    def _create(self, ssh):
        """
        Attempts to create a project through gerrit ssh commands.

        @param ssh - gerrit.SSH object

        """
        if self.create:
            cmd = 'gerrit create-project %s' % quote(self.name)
            retcode, text = ssh.exec_once(cmd)

    def _config(self, gerrit_config, groups):
        """
        Builds the groups file and project.config file for a project.

        @param gerrit_config - Dict Gerrit section of configuration
        @param groups - List of groups

        """
        if not self.config:
            return

        msg = "Project %s: Configuring." % self.name
        logger.info(msg)
        print msg

        repo_dir = '~/tmp'
        repo_dir = os.path.expanduser(repo_dir)
        repo_dir = os.path.abspath(repo_dir)

        uuid_dir = str(uuid4())
        repo_dir = os.path.join(repo_dir, uuid_dir)

        # Make Empty directory - We want this to stop and fail on OSError
        logger.debug(
            "Project %s: Creating directory %s" % (self.name, repo_dir)
        )
        os.makedirs(repo_dir)

        # Save the current working directory
        old_cwd = os.getcwd()

        indicator = gerrit_config['was-here-indicator']

        origin = 'origin'

        try:
            # Change cwd to that repo
            os.chdir(repo_dir)

            # Git init empty directory
            git.init()

            # Add remote origin
            ssh_url = 'ssh://%s@%s:%s/%s' % (
                gerrit_config['username'],
                gerrit_config['host'],
                gerrit_config['port'],
                self.name
            )

            git.add_remote(origin, ssh_url)

            # Fetch refs/meta/config for project
            refspec = 'refs/meta/config:refs/remotes/origin/meta/config'
            git.fetch(origin, refspec)

            # Checkout refs/meta/config
            git.checkout_branch('meta/config')

            repo_modified = False
            # Update groups file
            # Check to see if groups was already touched by this tool.
            _file = os.path.join(repo_dir, 'groups')
            if not file_contains(_file, indicator):
                logger.info("Project %s: writing groups file" % self.name)
                # Create entire new groups file
                contents = groups_file_contents(groups, indicator)
                with open(_file, 'w') as f:
                    f.write(contents)
                repo_modified = True

            # Update project.config file
            # Check to see if this file was already touched by this tool.
            _file = os.path.join(repo_dir, 'project.config')
            if not file_contains(_file, indicator):
                logger.info(
                    "Project %s: Writing project.config file" % self.name
                )
                # Create the new project.config file
                contents = project_config_contents(self.config, indicator)
                with open(_file, 'w') as f:
                    f.write(contents)
                repo_modified = True

            if repo_modified:
                # Git config user.email
                git.set_config('user.email', gerrit_config['git-config-email'])

                # Git config user.name
                git.set_config('user.name', gerrit_config['git-config-name'])

                # Add groups and project.config
                git.add(['groups', 'project.config'])

                # Git commit
                git.commit(message='Setting up %s' % self.name)

                # Git push
                git.push(origin, refspecs='meta/config:refs/meta/config')
                logger.info("Project %s: pushed configuration." % self.name)

            else:
                msg = "Project %s: groups and project.config already modified." \
                      % self.name
                logger.info(msg)
                print msg

        finally:
            # Change to old current working directory
            os.chdir(old_cwd)

            # Attempt to clean up created directory
            shutil.rmtree(repo_dir)

    def _sync(self, gerrit_config):
        """
        Pushes all normal branches from a source repo to gerrit.

        @param gerrit_config - Dictionary gerrit portion of configuration.

        """
        # Only sync if source repo is provided.
        if not self.source:
            return

        msg = "Project %s: syncing with repo %s." % (self.name, self.source)
        logger.info(msg)
        print msg

        repo_dir = '~/tmp'
        repo_dir = os.path.expanduser(repo_dir)
        repo_dir = os.path.abspath(repo_dir)

        # Make Empty directory - We want this to stop and fail on OSError
        if not os.path.isdir(repo_dir):
            os.makedirs(repo_dir)
            logger.debug(
                "Project %s: Created directory %s" % (self.name, repo_dir)
            )

        # Save the current working directory
        old_cwd = os.getcwd()

        try:
            # Change cwd to that repo
            os.chdir(repo_dir)

            uuid_dir = str(uuid4())
            repo_dir = os.path.join(repo_dir, uuid_dir)

            # Do a git clone --bare <source_repo>
            git.clone(self.source, name=uuid_dir, bare=True)

            # Change to bare cloned directory
            os.chdir(uuid_dir)

            # Add remote named gerrit
            ssh_url = 'ssh://%s@%s:%s/%s' % (
                gerrit_config['username'],
                gerrit_config['host'],
                gerrit_config['port'],
                self.name
            )
            git.add_remote('gerrit', ssh_url)

            # Grab origin refs
            origin_refset = git.remote_refs('origin', heads=True, tags=True)

            # Grab gerrit refs
            gerrit_refset = git.remote_refs('gerrit', heads=True)

            prune_refset = gerrit_refset - origin_refset
            if self.preserve_prefix:
                msg = "Project %s: Preserving refs with prefixes of %s" \
                      % (self.name, self.preserve_prefix)
                logger.debug(msg)
                heads_prefix = "refs/heads/%s" % self.preserve_prefix
                tags_prefix = "refs/tags/%s" % self.preserve_prefix
                keep = lambda ref: not ref.startswith(heads_prefix) and \
                    not ref.startswith(tags_prefix)
                prune_refset = filter(keep, prune_refset)

            colonize = lambda ref: ':%s' % ref
            prune_refset = map(colonize, prune_refset)

            # Do a git push --all
            git.push('gerrit', all_=True)

            # Remove branches no longer needed
            if prune_refset:
                git.push('gerrit', refspecs=prune_refset)

        finally:
            # Change to old current working directory
            os.chdir(old_cwd)

            # Attempt to clean up created directory
            shutil.rmtree(repo_dir)

    def ensure(self, ssh, gerrit_config, groups):

        msg = "Project %s: Ensuring present." % self.name
        logger.info(msg)
        print msg

        # Create Project if needed
        self._create(ssh)

        # Create submit a configuration if needed
        self._config(gerrit_config, groups)

        # Sync with source repo if needed
        self._sync(gerrit_config)


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
        msg = "Unable to retrieve list of gerrit groups."
        logger.error(msg)
        print msg
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
    """
    Creates the contents of a groups file to be saved with a project's
    configuration.

    @param groups - List of gerrit.Group objects
    @param indicator - String to prepend to beginning of contents
        indicating this tool was run.
    @return String

    """
    _buffer = StringIO.StringIO()
    if len(indicator) > 0:
        _buffer.write(indicator)
        _buffer.write("\n")
    for g in groups:
        _buffer.write("%s\t%s\n" % (g.uuid, g.name))
    return _buffer.getvalue()


def project_config_contents(source_file, indicator=""):
    """
    Creates the contents of a project configuration file. Prepends
    a "I was here" to the beginning of the file.

    @param source_file - String file name
    @param indicator - String indicator
    @return String
    """
    _buffer = StringIO.StringIO()
    if len(indicator) > 0:
        _buffer.write(indicator)
        _buffer.write("\n")
    with open(source_file, 'r') as f:
        _buffer.write(f.read())
    return _buffer.getvalue()


def file_contains(_file, indicator):
    """
    Checks if indicator is in file.

    @param _file - String file name
    @param indicator - String to check for
    @return Boolean

    """
    # Check if file exists first
    if not os.path.isfile(_file):
        return False

    # Read contents
    with open(_file, 'r') as f:
        contents = f.read()
    return indicator in contents
