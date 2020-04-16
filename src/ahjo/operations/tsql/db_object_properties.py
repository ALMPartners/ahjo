# Ahjo - Database deployment framework
#
# Copyright 2019, 2020 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for updating database object properties (descriptions).

Global variable EXCLUDED_SCHEMAS holds list of schemas that should
be excluded from update.

Global variable DOCS_DIR holds the documentation path of project.

Global variable DB_OBJECTS is a list of dictionaries holding
information about:
- which query to use to fetch metadata of specific db objects, for example views
- where to store fetched metadata and valid descriptions (CSV)
- column mapping of previously mentioned metadata query and CSV
- list of column indexes whose values form an unique object key
"""
import csv
from logging import getLogger
from os import makedirs, path

from ahjo.context import AHJO_PATH
from ahjo.database_utilities import execute_query, get_schema_names
from ahjo.operation_manager import OperationManager

logger = getLogger('ahjo')

EXCLUDED_SCHEMAS = ['db_accessadmin', 'db_backupoperator', 'db_datareader', 'db_datawriter',
                    'db_ddladmin', 'db_denydatareader', 'db_denydatawriter', 'db_owner',
                    'db_securityadmin', 'guest', 'INFORMATION_SCHEMA', 'sys']
DOCS_DIR = 'docs/db_objects'
DB_OBJECTS = {
    'schema': {
        'csv': path.join(DOCS_DIR, 'schemas.csv'),
        'query': 'resources/sql/queries/schema_descriptions.sql',
        'columns': ['schema_name', 'meta_value', 'meta_type', 'object_type'],
        'key_columns': ['schema_name']
    },
    'procedure': {
        'csv': path.join(DOCS_DIR, 'procedures.csv'),
        'query': 'resources/sql/queries/procedure_descriptions.sql',
        'columns': ['schema_name', 'object_name', 'meta_value', 'meta_type', 'object_type'],
        'key_columns': ['schema_name', 'object_name']
    },
    'function': {
        'csv': path.join(DOCS_DIR, 'functions.csv'),
        'query': 'resources/sql/queries/function_descriptions.sql',
        'columns': ['schema_name', 'object_name', 'meta_value', 'meta_type', 'object_type'],
        'key_columns': ['schema_name', 'object_name']
    },
    'table': {
        'csv': path.join(DOCS_DIR, 'tables.csv'),
        'query': 'resources/sql/queries/table_descriptions.sql',
        'columns': ['schema_name', 'object_name', 'meta_value', 'meta_type', 'object_type'],
        'key_columns': ['schema_name', 'object_name']
    },
    'view': {
        'csv': path.join(DOCS_DIR, 'views.csv'),
        'query': 'resources/sql/queries/view_descriptions.sql',
        'columns': ['schema_name', 'object_name', 'meta_value', 'meta_type', 'object_type'],
        'key_columns': ['schema_name', 'object_name']
    },
    'column': {
        'csv': path.join(DOCS_DIR, 'columns.csv'),
        'query': 'resources/sql/queries/column_descriptions.sql',
        'columns': ['schema_name', 'object_name', 'col_name', 'meta_value', 'meta_type', 'object_type', 'parent_type'],
        'key_columns': ['schema_name', 'object_name', 'col_name']
    }
}


def update_db_object_properties(engine, schema_list):
    """Update database object descriptions (CSV) to database.
    If schema_list is None, all schemas are updated.
    If schema_list is empty list, nothing is updated.
    Else schemas of schema_list are updated.

    Arguments
    ---------
    engine : sqlalchemy.engine.Engine
        SQL Alchemy engine.
    schema_list : list of str
        List of schemas to be documented.
    """
    with OperationManager('Updating metadata'):
        if schema_list is None:
            schema_list = [s for s in get_schema_names(engine) if s not in EXCLUDED_SCHEMAS]
        elif len(schema_list) == 0:
            logger.warning('No schemas allowed for update. Check variable "metadata_allowed_schemas".')
            return
        logger.debug(f'Updating metadata for schemas {", ".join(schema_list)}')
        for object_type, entry in DB_OBJECTS.items():
            source_file = entry['csv']
            columns = entry['columns']
            key_columns = entry['key_columns']
            metadata_query = entry['query']
            if not path.exists(source_file):
                logger.warning(f"Cannot update {object_type} metadata. File {source_file} does not exist")
                continue
            query_result = query_object_metadata(engine, metadata_query, schema_list)
            metadata_from_db = consume_query_result(query_result, key_columns, columns)
            with open(source_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=";")
                for object_name, object_csv_description in object_generator(reader, columns, key_columns):
                    if object_csv_description.get('schema_name') in schema_list:
                        object_db_metadata = metadata_from_db.get(object_name)
                        exec_update_extended_properties(engine, object_name, object_csv_description, object_db_metadata)


def exec_update_extended_properties(engine, object_name, object_csv_description, object_db_metadata):
    """Update object's extended properties (Description) by calling either
    procedure sp_addextendedproperty or sp_updateextendedproperty.
    If object_db_metadata is None, object does not exist in database.
    """
    try:
        if object_db_metadata is None:
            raise Exception('Object not found in database')
        object_type = object_db_metadata.get('object_type')
        parent_type = object_db_metadata.get('parent_type')
        if object_db_metadata.get('meta_value') is None:
            procedure_call = 'EXEC sp_addextendedproperty '
        else:
            procedure_call = 'EXEC sp_updateextendedproperty '
        procedure_call += '@name=?, @value=?, @level0type=?, @level0name=?'
        params = ['Description', object_csv_description.get('meta_value'), 'schema', object_csv_description.get('schema_name')]
        if object_type in ('view', 'table', 'function', 'procedure', 'column'):
            level1type = parent_type if parent_type is not None else object_type
            procedure_call += ', @level1type=?, @level1name=?'
            params.extend([level1type, object_csv_description.get('object_name')])
            if object_type == 'column':
                procedure_call += ', @level2type=?, @level2name=?'
                params.extend(['column', object_csv_description.get('col_name')])
        execute_query(engine, procedure_call, tuple(params))
    except Exception as err:
        logger.warning(f"Failed to update {object_name} description")
        logger.debug("Row data: " + ', '.join(object_csv_description.values()))
        logger.debug("Error message:")
        logger.debug(err)
        logger.info("------")


def update_csv_object_properties(engine, schema_list):
    """Write metadata to csv file.
    If project doesn't have docs directory, create it.

    If schema_list is None, all schemas are written to csv.
    If schema_list is empty list, nothing is written to csv.
    Else schemas of schema_list are written to csv.

    Arguments
    ---------
    engine : sqlalchemy.engine.Engine
        SQL Alchemy engine.
    schema_list : list of str
        List of schemas to be documented.
    """
    with OperationManager('Fetching metadata to CSV'):
        if not path.exists(DOCS_DIR):
            makedirs(DOCS_DIR, exist_ok=True)
        if schema_list is None:
            schema_list = [s for s in get_schema_names(engine) if s not in EXCLUDED_SCHEMAS]
        elif len(schema_list) == 0:
            logger.warning('No schemas allowed for document. Check variable "metadata_allowed_schemas".')
            return
        logger.debug(f'Fetching metadata for schemas {", ".join(schema_list)}')
        for _, entry in DB_OBJECTS.items():
            target_file = entry['csv']
            columns = entry['columns']
            key_columns = entry['key_columns']
            metadata_query = entry['query']
            query_result = query_object_metadata(engine, metadata_query, schema_list)
            with open(target_file, 'w+', encoding='utf-8', newline='') as f:
                writer = csv.writer(f, delimiter=";")
                for key, val in object_generator(query_result, columns, key_columns):
                    if val.get('meta_type') is None or val.get('meta_type') == "Description":
                        writer.writerow(key.split('.') + [val.get('meta_value')])
        logger.debug('Metadata fetched')


def query_object_metadata(engine, metadata_query, schema_list):
    query_path = path.join(AHJO_PATH, metadata_query)
    return prepare_and_exec_query(engine, query_path=query_path, param_list=schema_list)


def consume_query_result(query_result, key_columns, columns):
    query_result_as_dict = {}
    for key, val in object_generator(query_result, columns, key_columns):
        query_result_as_dict[key] = val
    return query_result_as_dict


def prepare_and_exec_query(engine, query_path, param_list):
    """Open query from query_path and set correct amount of
    parameter placeholders to question mark. Finally, execute query."""
    with open(query_path, 'r', encoding='utf-8') as file:
        query = file.read()
    param_placeholder = ','.join(['?'] * len(param_list))
    query = query.replace('?', param_placeholder)
    result = execute_query(engine, query=query, variables=tuple(param_list))
    return result


def object_generator(iterable, columns, key_columns):
    """Transform row to tuple of object_key (str) and object_attrs (dict).

    Object key is formed by joining the values of key_columns and object_attrs
    is a dictionary holding all available row columns and values."""
    for row in iterable:
        object_key = '.'.join([row[i] for i, _ in enumerate(key_columns)])
        object_attrs = {}
        for index, column in enumerate(columns):
            if len(row) > index:
                object_attrs[column] = row[index]
        yield object_key, object_attrs
