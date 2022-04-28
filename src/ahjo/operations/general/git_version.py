# Ahjo - Database deployment framework
#
# Copyright 2019, 2020, 2021 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for Git version operations."""
import os
from logging import getLogger
from shlex import split
from subprocess import check_output
from typing import Tuple

from ahjo.database_utilities import execute_query
from ahjo.operation_manager import OperationManager
from ahjo.interface_methods import load_json_conf
from sqlalchemy import Column, MetaData, String, Table
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoSuchTableError
from pathlib import PurePath, Path

logger = getLogger('ahjo')


def _sqla_git_table(metadata: MetaData, git_table_schema: str, git_table: str) -> Table:
    """Return Git table definition given by schema and table name."""
    return Table(
        git_table, metadata,
        Column('Repository', String(50), primary_key=True),
        Column('Branch', String(50), primary_key=True),
        Column('Commit', String(50)),
        schema=git_table_schema
    )


def update_git_version(engine: Engine, git_table_schema: str, git_table: str, repository: str = None, git_version_info_path: str = None):
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
            _update_git_db_record(engine, git_table_schema,
                                  git_table, repository, branch, commit)
        except Exception as error:
            logger.error('Failed to update Git version table. See log for detailed error message.')
            logger.debug(error)


def _load_git_commit_info_json(git_version_info_path: str) -> Tuple[str, str, str]:
    """Retrieve git commit information from a JSON file. 
    Fails if the file is not found or properly defined.
    """
    git_version_info = load_json_conf(git_version_info_path)
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


def _update_git_db_record(engine: Engine, git_table_schema: str, git_table: str, repository: str, branch: str, commit: str):
    """Update or create a Git version table."""
    metadata = MetaData(engine)
    try:
        git_version_table = Table(git_table, metadata, autoload=True, schema=git_table_schema)
    except NoSuchTableError as error:
        logger.info(
            f'Table {git_table_schema + "." + git_table} not found. Creating the table.')
        git_version_table = _sqla_git_table(metadata, git_table_schema, git_table)
        try:
            metadata.create_all()
        except Exception as error:
            raise Exception(
                'Git version table creation failed. See log for detailed error message.') from error
    git_version_table_columns = [col.name for col in git_version_table.c]
    if 'Commit_hash' in git_version_table_columns:
        logger.info(f'Re-creating table {git_table_schema + "." + git_table}.')
        try:
            metadata.drop_all()
            new_metadata = MetaData(engine)
            git_version_table = _sqla_git_table(new_metadata, git_table_schema, git_table)
            new_metadata.create_all()
        except Exception as error:
            raise Exception(
                'Failed to re-create Git version table. See log for detailed error message.') from error
    logger.info(f"Repository: {repository}")
    logger.info(f"Branch: {branch}")
    logger.info(f"Version: {commit}")
    engine.execute(git_version_table.delete())
    update_query = git_version_table.insert().values(Repository=repository,
                                                     Branch=branch,
                                                     Commit=commit)
    engine.execute(update_query)


def print_git_version(engine: Engine, git_table_schema: str, git_table: str):
    with OperationManager('Checking Git version from database'):
        try:
            metadata = MetaData(engine)
            git_version_table = _sqla_git_table(
                metadata, git_table_schema, git_table)
            git_version_query = git_version_table.select()
            result = execute_query(engine=engine, query=git_version_query)[0]
            repository, branch, version = result
            logger.info(f"Repository: {repository}")
            logger.info(f"Branch: {branch}")
            logger.info(f"Version: {version}")
        except Exception as error:
            logger.error(
                'Failed to read GIT version table. See log for detailed error message.')
            logger.debug(error)
