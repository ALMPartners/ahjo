"""Fixtures for preparing sample projects for test run.

When you add new sample projects...

@pytest.fixture(scope='session')
def new_sample(prepared_sample):
    return prepared_sample(
        sample_name='new_sample_project',
        host_param='new_host_param',
        port_param='new_port_param',
        usrn_param='new_username_param',
        pass_param='new_password_param'
    )
"""
from base64 import b64encode
from distutils.dir_util import copy_tree
from os import environ, getcwd, path

import commentjson as json
import pytest


PROJECT_ROOT = getcwd()


@pytest.fixture(scope='session')
def project_root():
    return PROJECT_ROOT


@pytest.fixture(scope='session')
def git_setup(project_root):
    environ["GIT_DIR"] = path.join(project_root, '.git')


@pytest.fixture(scope='session')
def ahjo_config():
    """Return read sample Ahjo config.
    This fixture is used when creating engine fixture.
    """
    def read_samples_ahjo_config(sample_directory):
        sample_config = path.join(sample_directory, 'config_development.jsonc')
        with open(sample_config) as f:
            config = json.load(f)
            config = config['BACKEND']
        return config
    return read_samples_ahjo_config


@pytest.fixture(scope='session')
def prepared_sample(tmpdir_factory, pytestconfig):
    def prepare_sample_for_tests(sample_name, host_param, port_param, usrn_param, pass_param):
        sample_directory = tmpdir_factory.mktemp(sample_name).strpath
        copy_sample_project(pytestconfig.rootdir,
                            sample_name, sample_directory)
        rewrite_sample_configuration(
            sample_directory,
            pytestconfig.getoption(host_param),
            pytestconfig.getoption(port_param)
        )
        write_sample_password_files(
            sample_directory,
            pytestconfig.getoption(usrn_param),
            pytestconfig.getoption(pass_param)
        )
        return sample_directory
    return prepare_sample_for_tests


def copy_sample_project(test_root, sample_name, sample_target):
    """Copy sample project to temporary directory."""
    tests_dir = path.join(test_root, 'test')
    sample_source = path.join(tests_dir, 'samples', sample_name)
    copy_tree(sample_source, sample_target)


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
    username_file = path.join(sample_root, 'username')
    username = 'cred=' + username
    with open(username_file, 'w', encoding='utf-8') as f:
        f.write(username)
    password_file = path.join(sample_root, 'password')
    password = 'cred=' + b64encode(password.encode()).decode()
    with open(password_file, 'w', encoding='utf-8') as f:
        f.write(password)
