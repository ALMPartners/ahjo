# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for git version operations."""
from shlex import split
from subprocess import check_output
from logging import getLogger

from sqlalchemy import Table, Column, String, MetaData

from ahjo.database_utilities import execute_query
from ahjo.operation_manager import OperationManager

logger = getLogger('ahjo')


def _sqla_git_table(engine, git_table_schema, git_table):
    """Makes git table definition given by schema and table names
    """
    git_table_meta = MetaData(engine)
    git_version_table = Table(
        git_table, git_table_meta,
        Column('Repository', String(50), primary_key=True),
        Column('Branch', String(50), primary_key=True),
        Column('Commit_hash', String(50)),
        schema=git_table_schema
    )
    return git_version_table, git_table_meta


def update_git_version(engine, git_table_schema, git_table, repository=None):
    """Stores the git version to database.
    Alembic version does not catch changes to views and procedures, but git version catches.
    """
    git_table_name = git_table_schema + "." + git_table

    with OperationManager("Updating GIT version table"):
        logger.info(f'GIT version table: {git_table_name}')
        try:
             # get the repository info and commit info
            if repository is None:
                origin_url_command = split("git config --get remote.origin.url")
                repository = check_output(origin_url_command).decode("utf-8").strip()
                if repository is None:
                    repository = ''
            branch, commit = _get_git_commit_info()
        except Exception as error:
            logger.error('Failed to retrieve GIT commit hash. See log for detailed error message.')
            logger.debug(error)
            return

        _update_git_db_record(engine, git_table_schema, git_table, repository, branch, commit)


def _update_git_db_record(engine, git_table_schema, git_table, repository, branch, commit):
    """Updates or creates a git version table.
    """
    git_version_table, meta = _sqla_git_table(engine, git_table_schema, git_table)
    
    if not engine.dialect.has_table(engine, git_table, schema=git_table_schema):
        logger.info(f'Table {git_table_schema + "." + git_table} not found. Creating the table.')
        try:
            meta.create_all()
        except Exception as error:
            logger.info('GIT version table creation failed. See log for detailed error message.')
            logger.debug(error)
            return
    try:
        logger.info(f"Repository: {repository}")
        logger.info(f"Branch: {branch}")
        logger.info(f"Version: {commit}")
        engine.execute(git_version_table.delete())
        update_query = git_version_table.insert().values(Repository=repository,
                                                         Branch=branch,
                                                         Commit_hash=commit)
        engine.execute(update_query)
    except Exception as error:
        logger.error('Failed to update GIT version table. See log for detailed error message.')
        logger.debug(error)


def _get_git_commit_info():
    """Gets branch and commit infromation with rev-parse command.
    Can fail if git repository is not initialized.
    """
    banch_command = split("git rev-parse --abbrev-ref HEAD")
    branch = check_output(banch_command).decode("utf-8").strip()
    commit_command = ['git', 'rev-parse', branch]
    commit = check_output(commit_command).decode("utf-8").strip()
    return branch, commit



def print_git_version(engine, git_table_schema, git_table):
    with OperationManager('Checking GIT commit- version from database'):
        try:
            git_version_table, _ = _sqla_git_table(engine, git_table_schema, git_table)
            git_version_query = git_version_table.select()
            result = execute_query(engine=engine, query=git_version_query)[0]
            repository, branch, version = result
            logger.info(f"Repository: {repository}")
            logger.info(f"Branch: {branch}")
            logger.info(f"Version: {version}")
        except Exception as error:
            logger.error('Failed to read GIT version table. See log for detailed error message.')
            logger.debug(error)
