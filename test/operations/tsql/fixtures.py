"""Fixtures related to tsql tests."""
from distutils.dir_util import copy_tree
from os import path
from subprocess import Popen, PIPE
from base64 import b64encode

import commentjson as json
import pytest


@pytest.fixture(scope='session')
def mssql_host(request):
    return request.config.getoption("mssql_host")


@pytest.fixture(scope='session')
def mssql_port(request):
    return request.config.getoption("mssql_port")


@pytest.fixture(scope='session')
def mssql_username(request):
    return request.config.getoption("mssql_username")


@pytest.fixture(scope='session')
def mssql_password(request):
    return request.config.getoption("mssql_password")


@pytest.fixture(scope='session')
def tsql_setup_and_teardown(pytestconfig, tmpdir_factory):
    """Copy MSSQL project to temporary dir.
    Rewrite configurations and create credential files.
    Init database for testing using Ahjo action 'init'.
    Execute tsql tests.
    Delete database using custom Ahjo action 'delete-database'.
    """
    sample_directory = tmpdir_factory.mktemp("mssql_project").strpath
    copy_sample_project(pytestconfig.rootdir, sample_directory)
    rewrite_sample_configuration(
        sample_directory,
        pytestconfig.getoption('mssql_host'),
        pytestconfig.getoption('mssql_port')
    )
    write_sample_password_files(
        sample_directory,
        pytestconfig.getoption('mssql_username'),
        pytestconfig.getoption('mssql_password')
    )
    # ahjo init
    p = Popen(['ahjo', 'init', 'config_development.jsonc'],
              cwd=sample_directory, stdin=PIPE)
    p.communicate(input='y\n'.encode())
    yield
    p = Popen(['ahjo', 'delete-database', 'config_development.jsonc'],
              cwd=sample_directory, stdin=PIPE)
    p.communicate(input='y\n'.encode())


def copy_sample_project(test_root, sample_target):
    tests_dir = path.join(test_root, 'test')
    mssql_sample = path.join(tests_dir, 'samples', 'mssql_project')
    copy_tree(mssql_sample, sample_target)


def rewrite_sample_configuration(sample_root, hostname, port_number):
    """Open sample project configuration file and rewrite
    server hostname, port number, username file path and password file path.
    """
    test_configuration = path.join(sample_root, 'config_development.jsonc')
    with open(test_configuration, 'r') as f:
        config = json.load(f)
    config['BACKEND']['target_server_hostname'] = hostname
    config['BACKEND']['sql_port'] = port_number
    config['BACKEND']['username_file'] = path.join(sample_root, 'username')
    config['BACKEND']['password_file'] = path.join(sample_root, 'password')
    with open(test_configuration, 'w') as f:
        json.dump(config, f)


def write_sample_password_files(sample_root, username, password):
    """Create files containing server credentials."""
    # use ahjo.credential_handler.obfuscate_credentials?
    username_file = path.join(sample_root, 'username')
    username = 'cred=' + username
    with open(username_file, 'w', encoding='utf-8') as f:
        f.write(username)
    password_file = path.join(sample_root, 'password')
    password = 'cred=' + b64encode(password.encode()).decode()
    with open(password_file, 'w', encoding='utf-8') as f:
        f.write(password)
