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
import csv
from argparse import Namespace
from base64 import b64encode
from shutil import copytree
from os import environ, getcwd, path

import json
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table

PROJECT_ROOT = getcwd()
SAMPLE_DATA_DIR = './database/data'


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
        sample_config = path.join(sample_directory, 'config_development.json')
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
    copytree(sample_source, sample_target, dirs_exist_ok=True)


def rewrite_sample_configuration(sample_root, hostname, port_number):
    """Open sample project configuration file and rewrite
    server hostname, port number, username file path and password file path.
    """
    test_configuration = path.join(sample_root, 'config_development.json')
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


@pytest.fixture(scope='function')
def run_alembic_action():
    """When executing, CWD must be set correctly to sample root!"""
    def execute_alembic(action, target):
        alembic_config = Config('alembic.ini')
        # main section options are set when main section is read
        main_section = alembic_config.config_ini_section
        alembic_config.get_section(main_section)
        alembic_config.cmd_opts = Namespace(
            x=["main_config=config_development.json"])
        if action == 'upgrade':
            command.upgrade(alembic_config, target)
        elif action == 'downgrade':
            command.downgrade(alembic_config, target)
    return execute_alembic


@pytest.fixture(scope='function')
def populate_table():
    """When executing, CWD must be set correctly to sample root!"""
    def insert_to_table(engine, table_name):
        source_file = path.join(SAMPLE_DATA_DIR, table_name)
        splitted = table_name.split('.')
        if len(splitted) > 1:
            table_name = splitted[1]
            table_schema = splitted[0]
            target_table = Table(
                table_name, 
                MetaData(), 
                schema=table_schema, 
                autoload_with=engine
            )
        else:
            target_table = Table(
                table_name, 
                MetaData(), 
                autoload_with=engine
            )
        with engine.begin() as connection:
            for rows in chunkreader(source_file):
                connection.execute(target_table.insert(), rows)
    return insert_to_table


def chunkreader(file_path, chunksize=200):
    with open(file_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f, delimiter=';')
        chunk = []
        for i, line in enumerate(reader):
            if (i % chunksize == 0 and i > 0):
                yield chunk
                chunk = []
            chunk.append(line)
        yield chunk
