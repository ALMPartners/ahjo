# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
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

from ahjo.database_utilities import execute_query, get_schema_names
from ahjo.operation_manager import OperationManager

console_logger = getLogger('ahjo.console')
logger = getLogger('ahjo.complete')

EXCLUDED_SCHEMAS = ['db_accessadmin', 'db_backupoperator', 'db_datareader', 'db_datawriter',
                    'db_ddladmin', 'db_denydatareader', 'db_denydatawriter', 'db_owner',
                    'db_securityadmin', 'guest', 'INFORMATION_SCHEMA', 'sys']
DOCS_DIR = 'docs/db_objects'
DB_OBJECTS = {
    'schema': {
        'meta_query': 'resources/sql/queries/schema_descriptions.sql',
        'csv': path.join(DOCS_DIR, 'schemas.csv'),
        'col_map': {0: 'schema_name', 1: 'meta_value', 2: 'meta_type', 3: 'object_type'},
        'key_cols': [0]
    },
    'procedure': {
        'meta_query': 'resources/sql/queries/procedure_descriptions.sql',
        'csv': path.join(DOCS_DIR, 'procedures.csv'),
        'col_map': {0: 'schema_name', 1: 'object_name', 2: 'meta_value', 3: 'meta_type', 4: 'object_type'},
        'key_cols': [0, 1]
    },
    'function': {
        'meta_query': 'resources/sql/queries/function_descriptions.sql',
        'csv': path.join(DOCS_DIR, 'functions.csv'),
        'col_map': {0: 'schema_name', 1: 'object_name', 2: 'meta_value', 3: 'meta_type', 4: 'object_type'},
        'key_cols': [0, 1]
    },
    'table': {
        'meta_query': 'resources/sql/queries/table_descriptions.sql',
        'csv': path.join(DOCS_DIR, 'tables.csv'),
        'col_map': {0: 'schema_name', 1: 'object_name', 2: 'meta_value', 3: 'meta_type', 4: 'object_type'},
        'key_cols': [0, 1]
    },
    'view': {
        'meta_query': 'resources/sql/queries/view_descriptions.sql',
        'csv': path.join(DOCS_DIR, 'views.csv'),
        'col_map': {0: 'schema_name', 1: 'object_name', 2: 'meta_value', 3: 'meta_type', 4: 'object_type'},
        'key_cols': [0, 1]
    },
    'column': {
        'meta_query': 'resources/sql/queries/column_descriptions.sql',
        'csv': path.join(DOCS_DIR, 'columns.csv'),
        'col_map': {0: 'schema_name', 1: 'object_name', 2: 'col_name', 3: 'meta_value', 4: 'meta_type', 5: 'object_type', 6: 'parent_type'},
        'key_cols': [0, 1, 2]
    }
}


def update_db_object_properties(engine, ahjo_path, schema_list):
    """Update database object descriptions (CSV) to database.
    If schema_list is None, all schemas are updated.
    If schema_list is empty list, nothing is updated.
    Else schemas of schema_list are updated.

    Arguments
    ---------
    engine : sqlalchemy.engine.Engine
        SQL Alchemy engine.
    ahjo_path : str
        Path where Ahjo is installed.
    schema_list : list of str
        List of schemas to be documented.
    """
    with OperationManager('Updating metadata'):
        if schema_list is None:
            schema_list = [s for s in get_schema_names(engine) if s not in EXCLUDED_SCHEMAS]
        elif len(schema_list) == 0:
            console_logger.info('No schemas allowed for update. Check variable "metadata_allowed_schemas".')
            return
        for key, entry in DB_OBJECTS.items():
            if path.exists(entry['csv']):
                with open(entry['csv'], encoding='utf-8') as csv_file:
                    reader = csv.reader(csv_file, delimiter=";")
                    object_descriptions = rows_to_dict(
                        iterable_rows=reader,
                        key_cols=entry['key_cols'],
                        col_mapping=entry['col_map']
                        )
                meta_query_path = path.join(ahjo_path, entry['meta_query'])
                meta_query_result = prepare_and_exec_query(engine, query_path=meta_query_path, param_list=schema_list)
                object_metadata = rows_to_dict(
                    iterable_rows=meta_query_result,
                    key_cols=entry['key_cols'],
                    col_mapping=entry['col_map']
                    )
                exec_update_extended_properties(engine, object_descriptions, object_metadata)
            else:
                console_logger.info(f"Cannot update {key} metadata. File {entry['csv']} does not exist")


def exec_update_extended_properties(engine, object_descriptions, object_metadata):
    """Loop object descriptions and update them to database by calling either
    procedure sp_addextendedproperty or sp_updateextendedproperty."""
    for object_name, object_desc in object_descriptions.items():
        try:
            object_meta = object_metadata[object_name]
            object_type = object_meta.get('object_type')
            parent_type = object_meta.get('parent_type')
            if object_meta.get('meta_value') is None:
                procedure_call = 'EXEC sp_addextendedproperty '
            else:
                procedure_call = 'EXEC sp_updateextendedproperty '
            procedure_call += '@name=?, @value=?, @level0type=?, @level0name=?'
            params = ['Description', object_desc.get('meta_value'), 'schema', object_desc.get('schema_name')]
            if object_type in ('view', 'table', 'function', 'procedure', 'column'):
                level1type = parent_type if parent_type is not None else object_type
                procedure_call += ', @level1type=?, @level1name=?'
                params.extend([level1type, object_desc.get('object_name')])
                if object_type == 'column':
                    procedure_call += ', @level2type=?, @level2name=?'
                    params.extend(['column', object_desc.get('col_name')])
            execute_query(engine, procedure_call, tuple(params))
        except Exception as err:
            console_logger.info(f"Failed to update {object_name} description")
            logger.info("Row data: " + ', '.join(object_desc.values()))
            logger.info("Error message:")
            logger.info(err)
            console_logger.info("------")


def update_csv_object_properties(engine, ahjo_path, schema_list):
    """Write metadata to csv file.
    If project doesn't have docs directory, create it.

    If schema_list is None, all schemas are written to csv.
    If schema_list is empty list, nothing is written to csv.
    Else schemas of schema_list are written to csv.

    Arguments
    ---------
    engine : sqlalchemy.engine.Engine
        SQL Alchemy engine.
    ahjo_path : str
        Path where Ahjo is installed.
    schema_list : list of str
        List of schemas to be documented.
    """
    with OperationManager('Fetching metadata to CSV'):
        if not path.exists(DOCS_DIR):
            makedirs(DOCS_DIR, exist_ok=True)
        if schema_list is None:
            schema_list = [s for s in get_schema_names(engine) if s not in EXCLUDED_SCHEMAS]
        elif len(schema_list) == 0:
            console_logger.info('No schemas allowed for document. Check variable "metadata_allowed_schemas".')
            return
        for _, entry in DB_OBJECTS.items():
            meta_query_path = path.join(ahjo_path, entry['meta_query'])
            meta_query_result = prepare_and_exec_query(engine, query_path=meta_query_path, param_list=schema_list)
            object_metadata = rows_to_dict(
                iterable_rows=meta_query_result,
                key_cols=entry['key_cols'],
                col_mapping=entry['col_map']
                )
            filtered_meta = [object_name.split('.') + [object_meta.get('meta_value')]
                             for object_name, object_meta in object_metadata.items()
                             if object_meta.get('meta_type') is None
                             or object_meta.get('meta_type') == "Description"]
            with open(entry['csv'], 'w+', encoding='utf-8', newline='') as csv_file:
                writer = csv.writer(csv_file, delimiter=";")
                writer.writerows(filtered_meta)
        console_logger.info('Metadata fetched')


def prepare_and_exec_query(engine, query_path, param_list):
    """Open query from query_path and set correct amount of
    parameter placeholders to question mark. Finally, execute query."""
    with open(query_path, 'r', encoding='utf-8') as file:
        query = file.read()
    param_placeholder = ','.join(['?'] * len(param_list))
    query = query.replace('?', param_placeholder)
    result = execute_query(engine, query=query, variables=tuple(param_list))
    return result


def rows_to_dict(iterable_rows, key_cols, col_mapping):
    """Loop rows and return a dictionary holding entries created from individual rows.
    Entry key is formed from key_cols of row and entry value
    is a dictionary holding row columns mapped according to col_mapping."""
    result_dict = {}
    for row in iterable_rows:
        row_key = '.'.join([row[i] for i in key_cols])
        result_dict[row_key] = {}
        for index, key in col_mapping.items():
            if len(row) > index:
                result_dict[row_key][key] = row[index]
    return result_dict
