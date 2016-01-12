gerrit-python-tools
===================

##gerrit-sync
This tool is used to create users, create groups, create projects and sync
projects. Users and groups that already exist will not be modified on subsequent
invocations.

####Usage
Invoke gerrit-sync with an optional argument for configuration file.
/etc/gerrit-python-tools/projects.yaml will be used by default when no
configuration file argument is provided.

```shell
gerrit-sync
```

##gerrit-python-tools
This was written for a scenario involving an upstream gerrit and a downstream
gerrit.  Downstream gerrit should receive code updates from upstream as
changes are merged in on upstream. Code changes that have successfully passed
review on downstream should be sent to upstream for review.

This tool will set up an event listener to both upstream and downstream and
will respond to gerrit events on either accordingly.

ref-updated events on configured projects on the upstream event stream will
cause a sync to downstream to take place.

comment-added events on configured projects on the downstream event stream
will cause a push to upstream for review if configured criteria is met.

####Usage
Invoke gerrit-python-tools with an optional argument for configuration file.
/etc/gerrit-python-tools/projects.yaml will be used by defauled when no
configuration file argument is provided.

```shell
gerrit-python-tools
```
##Configuration

###Logging
The configuration for logging is located at
/etc/gerrit-python-tools/logging.yaml. This may be made configurable in the
future. The log will always use a TimedRotatingFileHandler that switches over
at midnight.

Example:
```yaml
file: '/var/log/gerrit-python-tools/gerrit-sync'
level: 'info'
format: '%(asctime)s - %(levelname)s - %(message)s'
```

| Key    | Value |
| ---    | ----- |
| file   | where the log file should live |
| level  | one of: debug, info, warn, error, critical. At this time, only debug, info, and error are used in this code. |
| format | The format of a log message. |

### Everything else
Configuration for everything else should be in a single yaml file. By default,
this file is located at /etc/gerrit-python-tools/projects.yaml. This file
should contain the following sections

#### git-config
This section configures author information. gerrit-python-tools should only
be authoring changes when it is configured to manage project.config files for
downstream gerrit projects.
```yaml
git-config:
  email: 'someaddress@somedomain.com'
  name: 'joe somebody'
```
| Key   | Value |
| ----- | ----- |
| email | Email address of the author |
| name  | Name of the author |

gerrit-python-tools will run the following commands when authoring a
project.config.
```shell
git config user.name "<name>"
git config user.email "<email>"
```

#### gerrit
This section configures how to talk to a downstream gerrit.
```yaml
gerrit:
  host: localhost
  port: 29418
  username: YourUserName
  git-config-email: "someemailaddress@somedomain.com"
  git-config-name: "some name"
```
| Key          | Value |
| ------------ | ----- |
| host         | location of the downstream gerrit. Localhost by default |
| port         | ssh port of the downstream gerrit. 29418 by default |
| username     | Downstream gerrit username. 'SomeUser' by default |
| key_filename | Optional private key to use when ssh'ing to a downstream gerrit. Some features will not work if this is other than the default ssh key for the user running gerrit-python-tools |
| timeout      | Timeout in seconds for ssh'ing to downstream gerrit. 10 by default |
| keepalive    | Keepalive setting in seconds for ssh'ing to downstream gerrit. 60 by default |

####upstream
This section configures how to talk to the upstream gerrit.
```yaml
upstream:
  host: somehost
  port: 29418
  username: SomeUser
  timeout: 10
  keepalive: 60
  trigger: "Verified+2"
```
| Key          | Value |
| ------------ | ----- |
| host         | location of upstream gerrit. '' By default |
| port         | ssh port of upstream gerrit. 29418 by default |
| username     | Upstream gerrit username. 'SomeUser' by default |
| key_filename | Optional private key to use when ssh'ing to upstream gerrit |
| timeout      | Timeout in seconds for ssh'ing to upstream gerrit. 10 by default |
| keepalive    | Keepalive setting in seconds for ssh'ing to upstream gerrit. 60 by default |
| trigger      | Label and value to listen for on downstream gerrit that will cause an attempt to send to upstream. Default 'Verified+2' |

####upstream-labels
This section configures the labels that must have sufficient approvals before
a change can be sent to upstream for review. The section should be a yaml list
of labels. The labels defined here will emulate the MaxWithBlock behavior. All
projects will use these labels as criteria before sending to upstream unless
otherwise configured.

Note: This should be changed in the future to look at submit records from a
gerrit query.

```yaml
upstream-labels:
  - name: Code-Review
    min: -2
    max: 2
  - name: Verified
    min: -2
    max: 2
```
In the above sample, a code change must have a +2 in Verified and Code-Review,
both without a -2 before a change can be sent to upstream.

| Key | Value |
| --- | ----- |
| name | Name of the label |
| min | Minimum value of the label There cannot be an approval with the lowest value before a change can be sent to upstream. |
| max | Maximum value of the label. At least one approval with maximum value required before a change can be sent to upstream. |

####daemon
This section configures various parts of the gerrit-python-tools daemon.
```yaml
daemon:
  numthreads: 5
  sleep: 5
  delay: 120
  upstream: True
  sync: True
```
| Key        | Value |
| ---------- | ----- |
| numthreads | Number of worker threads. Defaults to 5 |
| sleep      | Number of seconds to wait upon recieving no events from upstream or downstream. Defaults to 5 |
| delay      | Number of seconds to wait upon recieving a ref-updated event on upstream before syncing to downstream. Defaults to 120 |
| upstream   | Whether or not to listen for events on downstream that will trigger a send to upstream. Defaults to True |
| sync       | Whether or not to listen for events on upstream that will trigger syncs to downstream. Defaults to True |

####Projects
This section configures the the projects that gerrit-python-tools will help
manage. This section accepts a yaml list of objects describing projects.

```yaml
projects:
  - name: All-Projects
    config: /etc/gerrit-python-tools/acls/All-Projects.config

  - name: upstream-project-1
    config: /etc/gerrit-python-tools/acls/project-1.config
    create: True
    source: 'https://github.com/YourUserName/project-1.git'
    upstream: True

  - name: downstream-project-2
    config: /etc/gerrit-python-tools/acls/project-2.config
    create: True
    source: 'https://github.com/YourUserName/project-2.git'

    # This is an example of how to specify upstream gating labels
    # per project.
  - name: upstream-project-3-special-labels
    create: True
    source: 'https://github.com/YourUserName/project-3.git'
    upstream-labels:
      - name: Special-Label
        min: -2
        max: 2
  - name: project1
    source: https://somegiturl/project1.git
    create: True
```

The following table describes the properties available per project:

| Key             | Value |
| --------------- | ----- |
| name            | Required. Name of the project as it appears in gerrit. |
| create          | Whether or not to create the project if it does not exist. Defaults to false |
| config          | Optional. Location of file that should be the project's project.config file. Used for access control to the project. |
| source          | Required. Location of the source repo that will be the basis of the gerrit project. Syncs will come from this location. |
| preserve_prefix | Optional. Define the prefix for branches that should be preserved and not deleted. |
| heads           | Optional. Whether or not to sync head branches. Defaults to true |
| tags            | Optional. Whether or not to sync tags. Defaults to false |
| force           | Whether or not to force commits when syncing. This is used to remove branches on downstream that no longer exist on upstream. This also allows gerrit-python-tools to overwrite refs that are not ancestors of a branch from upstream. Defaults to True. Setting this to False will remove the possibility of losing code present only on downstream, but downstream could become out of sync with upstream. |
| upstream        | Whether or not this project is an upstream project. Upstream projects will attempt to send approved code changes upstream. |
| upstream-labels | Define labels that are required before sending code changes on this project to upstream. Setting this will cause this project to no longer user the upstream-labels defined for all projects. |

####Groups
This section accepts a yaml list of objects describing gerrit groups. gerrit-python-tools will attempt to create groups. No action will be taken if the group already exists.

```yaml
groups:
  - name: core-devs
    owner: Administrators
    description: core developers with super powers.
  - name: "Continuous Integration Tools"
    owner: Administrators
    description: CI tools that need users belong here.
```

The following table describes the properties available to each group

| Key         | Value |
| ----------  | ----- |
| name        | Name of the group |
| owner       | Owning group of this group. |
| description | Description of the group |

####Users
This section accepts a yaml list of objects desribing gerrit users. gerrit-python-tools will attempt to create users. No action will be taken if the user already exists.

```yaml
users:
 - username: 'a-user-that-runs-tests'
   ssh-key: 'some ssh public key'
   groups:
     - "Continuous Integration Tools"
```

| Key      | Value |
| -------- | ----- |
| username | Gerrit username of the user |
| ssh-key  | public key of the user |
| groups   | list of groups that the user will belong to. |
