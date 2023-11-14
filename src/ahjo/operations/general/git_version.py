# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for Git operations."""
import os
from logging import getLogger
from shlex import split
from subprocess import check_output, run
from typing import Tuple, Union

from ahjo.interface_methods import rearrange_params
from ahjo.database_utilities import execute_query
from ahjo.operation_manager import OperationManager
from ahjo.interface_methods import load_conf
from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import NoSuchTableError
from pathlib import PurePath, Path

logger = getLogger('ahjo')


def _sqla_git_table(metadata: MetaData, git_table_schema: str, git_table: str) -> Table:
    """Return Git table definition given by schema and table name."""
    return Table(
        git_table, metadata,
        Column('Repository', String(255), primary_key=True),
        Column('Branch', String(255), primary_key=True),
        Column('Commit', String(50)),
        schema=git_table_schema
    )


@rearrange_params({"engine": "connectable"})
def update_git_version(connectable: Union[Engine, Connection], git_table_schema: str, git_table: str, repository: str = None, git_version_info_path: str = None):
    """Store the Git remote, branch and commit information to database.
    Alembic version does not catch changes to views and procedures, but git version catches.
    """
    with OperationManager("Updating Git version table"):
        try:
            default_git_version_info_path = PurePath(os.getcwd(), "git_version.json")
            if git_version_info_path:
                branch, commit, repository = _load_git_commit_info_json(
                    git_version_info_path = git_version_info_path
                )
            elif Path(default_git_version_info_path).is_file():
                branch, commit, repository = _load_git_commit_info_json(
                    git_version_info_path = default_git_version_info_path
                )                
            else:
                branch, commit = _get_git_commit_info()
                if repository is None:
                    origin_url_command = split("git config --get remote.origin.url")
                    repository = check_output(origin_url_command).decode("utf-8").strip()
                    if repository is None:
                        repository = ''                  
        except Exception as error:
            logger.error('Failed to retrieve Git commit. See log for detailed error message.')
            logger.debug(error)
            return
        try:
            logger.info("GIT version table: " + git_table_schema + "." + git_table)
            _update_git_db_record(connectable, git_table_schema,
                                  git_table, repository, branch, commit)
        except Exception as error:
            logger.error('Failed to update Git version table. See log for detailed error message.')
            logger.debug(error)


def _load_git_commit_info_json(git_version_info_path: str) -> Tuple[str, str, str]:
    """Retrieve git commit information from a JSON file. 
    Fails if the file is not found or properly defined.
    """
    git_version_info = load_conf(git_version_info_path)
    return git_version_info["branch"], git_version_info["commit"], git_version_info["repository"]

def _get_git_commit_info() -> Tuple[str, str]:
    """Retrieve branch and commit information with 'git rev-parse'
    and 'git describe' commands.

    Can fail if Git repository is not initialized.
    """
    banch_command = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    branch = check_output(banch_command).decode("utf-8").strip()
    commit_command = ['git', 'describe', '--always', '--tags']
    commit = check_output(commit_command).decode("utf-8").strip()
    return branch, commit


def _get_previous_tag(tag: str) -> str:
    """Retrieve the previous tag with 'git describe' command.
    Can fail if tags are not found.
    """
    return check_output(["git", "describe", "--tags", "--abbrev=0", tag + "^"]).decode("utf-8").strip()


def _get_all_tags() -> list:
    """Retrieve the list of all tags with 
    'git tag' command.

    Can fail if tags are not found.
    """
    return check_output(["git", "tag", "--sort=-taggerdate"]).decode("utf-8").strip().split("\n")


def _checkout_tag(tag: str):
    """Checkout a tag with 'git checkout' command.
    Can fail if tag is not found.
    """
    run(["git", "checkout", "tags/" + tag])
    _, checkout_version =_get_git_commit_info()
    if checkout_version != tag:
        raise Exception(f"Failed to checkout git version: {tag}")


def _get_all_files_in_staging_area():
    """ Retrieve all files in staging area with 'git diff' command. """
    return check_output(["git", "diff", "--cached", "--name-only"]).decode("utf-8").strip().split("\n")


def _get_all_files_in_working_directory():
    """ Retrieve all files in working directory with 'git ls-tree' command. """
    _, commit = _get_git_commit_info()
    return check_output(["git", "ls-tree", "-r", "--name-only", commit]).decode("utf-8").strip().split("\n")


@rearrange_params({"engine": "connectable"})
def _update_git_db_record(connectable: Union[Engine, Connection], git_table_schema: str, git_table: str, repository: str, branch: str, commit: str):
    """Update or create a Git version table."""
    metadata = MetaData()
    try:
        git_version_table = Table(git_table, metadata, autoload_with=connectable, schema=git_table_schema)
    except NoSuchTableError as error:
        logger.info(
            f'Table {git_table_schema + "." + git_table} not found. Creating the table.')
        git_version_table = _sqla_git_table(metadata, git_table_schema, git_table)
        try:
            metadata.create_all(connectable)
        except Exception as error:
            raise Exception(
                'Git version table creation failed. See log for detailed error message.') from error
    git_version_table_columns = [col.name for col in git_version_table.c]
    if 'Commit_hash' in git_version_table_columns:
        logger.info(f'Re-creating table {git_table_schema + "." + git_table}.')
        try:
            metadata.drop_all(connectable)
            new_metadata = MetaData()
            git_version_table = _sqla_git_table(new_metadata, git_table_schema, git_table)
            new_metadata.create_all(connectable)
        except Exception as error:
            raise Exception(
                'Failed to re-create Git version table. See log for detailed error message.') from error
    logger.info(f"Repository: {repository}")
    logger.info(f"Branch: {branch}")
    logger.info(f"Version: {commit}")

    if type(connectable) == Engine:
        connection = connectable.connect()
        connection.execution_options(isolation_level="AUTOCOMMIT")
    else:
        connection = connectable

    connection.execute(git_version_table.delete())
    update_query = git_version_table.insert().values(
        Repository=repository,
        Branch=branch,
        Commit=commit
    )
    connection.execute(update_query)


@rearrange_params({"engine": "connectable"})
def _get_git_version(connectable: Union[Engine, Connection], git_table_schema: str, git_table: str):
    """Return the first row of the Git version table."""
    result = None
    try:
        metadata = MetaData()
        git_version_table = _sqla_git_table(metadata, git_table_schema, git_table)
        result = execute_query(connectable, query=git_version_table.select())[0]
    except Exception as error:
        logger.error('Failed to read GIT version table. See log for detailed error message.')
        logger.debug(error)
    return result


@rearrange_params({"engine": "connectable"})
def print_git_version(connectable: Union[Engine, Connection], git_table_schema: str, git_table: str):
    with OperationManager('Checking Git version from database'):
        repository, branch, version = _get_git_version(connectable, git_table_schema, git_table)
        logger.info(f"Repository: {repository}")
        logger.info(f"Branch: {branch}")
        logger.info(f"Version: {version}")


def get_git_hooks_path() -> str:
    """Return the path to the Git hooks directory."""
    git_hooks_path = check_output(["git", "rev-parse", "--git-path", "hooks"]).decode("utf-8").strip()
    if git_hooks_path == "":
        git_hooks_path = ".git/hooks"
    return git_hooks_path