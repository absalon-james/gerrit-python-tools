from setuptools import setup, find_packages
from gerrit_python_tools.meta import version, license

description = "Various tools in python for interacting with gerrit."
data_files = [
    ('/etc/gerrit-python-tools', ['sample-config.yaml','sample-logging.yaml'])
]

with open('README.md', 'r') as f:
    readme = f.read()

setup(
    name="gerrit_python_tools",
    version=version,
    description=description,
    long_description=readme,
    author="James Absalon",
    author_email="james.absalon@rackspace.com",
    license=license,
    packages=find_packages(),
    zip_safe=True,
    data_files=data_files,
    scripts=['bin/gerrit-sync']
)
