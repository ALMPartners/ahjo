# Ahjo - Database deployment framework
#
# Copyright 2019 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for updating database object properties.

Global variable DOCS_DIR holds the documentation path of project.

Global variable DB_OBJECTS is a list of dictionaries holding
information about:
- which query to use to fetch metadata of specific db objects, for example views
- how many columns the fetched metadata result set has
- where to store fetched metadata
- what procedure to use when inserting updated metadata back to database
"""

import csv
from logging import getLogger
from os import makedirs, path

from ahjo.database_utilities import execute_query
from ahjo.operation_manager import OperationManager

console_logger = getLogger('ahjo.console')

DOCS_DIR = 'docs/db_objects'
DB_OBJECTS = [
    {
        'query': 'resources/sql/queries/schema_descriptions.sql',
        'csv': path.join(DOCS_DIR, 'schemas.csv'),
        'columns': 2
    },
    {
        'query': 'resources/sql/queries/procedure_descriptions.sql',
        'csv': path.join(DOCS_DIR, 'procedures.csv'),
        'columns': 3
    },
    {
        'query': 'resources/sql/queries/function_descriptions.sql',
        'csv': path.join(DOCS_DIR, 'functions.csv'),
        'columns': 3
    },
    {
        'query': 'resources/sql/queries/table_descriptions.sql',
        'csv': path.join(DOCS_DIR, 'tables.csv'),
        'columns': 3
    },
    {
        'query': 'resources/sql/queries/view_descriptions.sql',
        'csv': path.join(DOCS_DIR, 'views.csv'),
        'columns': 3
    },
    {
        'query': 'resources/sql/queries/column_descriptions.sql',
        'csv': path.join(DOCS_DIR, 'columns.csv'),
        'columns': 4
    }
]


def update_csv_object_properties(engine, ahjo_path, schema_list):
    """Write metadata to csv file.
    If project doesn't have docs directory, create it.

    Arguments
    ---------
    engine : sqlalchemy.engine.Engine
        SQL Alchemy engine.
    ahjo_path : str
        Path where Ahjo is installed.
    schema_list : list of str
        List of schemas to be documented.
    """
    with OperationManager('Fetching metadata to csv'):
        if not path.exists(DOCS_DIR):
            makedirs(DOCS_DIR, exist_ok=True)
        for entry in DB_OBJECTS:
            # Read query and set correct amount of parameter placeholders
            with open(path.join(ahjo_path, entry['query']), 'r', encoding='utf-8') as file:
                query = file.read()
            param_placeholder = ','.join(['?'] * len(schema_list))
            query = query.replace('?', param_placeholder)
            # pass parameters and execute query
            output = execute_query(engine, query=query, variables=tuple(schema_list))
            # filter output and write filtered output to csv
            ind = entry['columns']
            filtered_output = [row[:ind] for row in output if row[ind] is None or row[ind] == "Description"]
            with open(entry['csv'], 'w+', encoding='utf-8', newline='') as csv_file:
                writer = csv.writer(csv_file, delimiter=";")
                writer.writerows(filtered_output)
        console_logger.info('Metadata fetched')
