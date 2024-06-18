# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for database tests related operations."""

from ahjo.operations.general.sqlfiles import deploy_sqlfiles
from ahjo.context import Context
from logging import getLogger
from sqlalchemy import Table, insert
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine

logger = getLogger('ahjo')

class DatabaseTester:
    """Class for database tests related operations. 

    DatabaseTester class is used to run tests in the test folder and optionally save the results to the database.
    Each sql test file should return a result set where the first row contains the column names and the rest of the rows contain the data.
    The returned column names from the test file should match the column names of the test table where the test results are saved.
    Only the matching columns are saved to the database - the rest are ignored.
    For example, the test file could return the following result set which corresponds to the default test table columns:

    SELECT 
        StartTime,
        EndTime,
        TestName,
        Issue,
        Result
    FROM @RESULTS
    ORDER BY ID

    Attributes:
    -----------
    context: Context
        Context object.
    table: Table
        Table object where the test results are saved.
    connectable: Engine
        Engine object for connecting to the database.
    add_test_file_to_result: bool
        If True, the test file name is added to the test results.
    """

    def __init__(self, context: Context, table: Table = None, add_test_file_to_result: bool = True):
        """Constructor for DatabaseTester class.

        Arguments:
        -----------
        context: Context
            Context object.
        table: Table
            Table object where the test results are saved.
        add_test_file_to_result: bool
            If True, the test file name is added to the test results.
        """
        self.context = context
        self.table = table
        self.connectable = context.get_connectable()
        self.add_test_file_to_result = add_test_file_to_result
    
    def execute_test_files(self, test_folder: str, display_output: bool = True) -> dict:
        """Run the tests in the test folder and optionally save the results to the database.
        
        Arguments:
        -----------
        test_folder: str
            Folder containing the test files.
        display_output: bool
            If True, the test output is displayed.
        
        Returns:
        -----------
        dict
            Dict where key is the test file name and value is the test result.
        """
        file_results = deploy_sqlfiles(self.connectable, test_folder, "Running tests", display_output = display_output)
        if self.context.configuration.get("save_test_results_to_db", False):
            self.save_results_to_db(file_results)
        return file_results


    def save_results_to_db(self, file_results: dict):
        """Save the test results to the database. 
        
        Arguments:
        -----------
        file_results: dict
            Dict where key is the test file name and value is the test result. 
        """
        try:
            connectable = self.connectable

            # Get test table columns
            test_table_columns = [column.name for column in self.table.columns]

            # Output format: Dict where key is the test file name and value is the test result.
            for filepath, output in file_results.items():

                # Get the first row of the output as column names
                output_columns = output[0]
                
                # Get the intersection of the output columns and the table columns and get the indices of the columns to match the data
                columns = []
                column_indices = []
                for i, column in enumerate(output_columns):
                    if column in test_table_columns:
                        columns.append(column)
                        column_indices.append(i)

                if len(columns) == 0:
                    raise ValueError(f"No matching columns between the test output and the test table columns. Test output columns: {output_columns}, table columns: {test_table_columns}")
                
                # Create a list of dictionaries where key is the column name and value is the result data
                insert_list = []
                for row in output[1:]:

                    row_dict = {}
                    for i, column in zip(column_indices, columns):
                        row_dict[column] = row[i]

                    # Add the test file name to the row
                    if self.add_test_file_to_result:
                        row_dict["TestFile"] = filepath

                    insert_list.append(row_dict)
                
                # Save the results to the database
                with Session(connectable) as session:
                    session.execute(insert(self.table), insert_list)
                    if type(connectable) == Engine:
                        session.commit()

        except Exception as e:
            logger.error(f"Error saving test results to the database: {e}")
            raise e