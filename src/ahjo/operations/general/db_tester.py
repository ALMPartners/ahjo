# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for database tests related operations."""

from ahjo.operations.general.sqlfiles import deploy_sqlfiles
from typing import Union
from logging import getLogger
from sqlalchemy import Table, insert
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.sql import text

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
    connectable: Engine or Connection
        SQLAlchemy Engine or Connection object for database connection.
    table: Table
        Table object where the test results are saved.
    save_test_results_to_db: bool
        If True, the test results are saved to the database. Default is False.
    """

    def __init__(self, connectable: Union[Engine, Connection], table: Table = None, save_test_results_to_db: bool = False):
        """Constructor for DatabaseTester class.

        Arguments:
        -----------
        connectable: Engine or Connection
            SQLAlchemy Engine or Connection object for database connection.
        table: Table
            Table object where the test results are saved.
        save_test_results_to_db: bool
            If True, the test results are saved to the database. Default is False.
        """
        self.connectable = connectable
        self.table = table
        self.save_test_results_to_db = save_test_results_to_db
    

    def set_save_test_results_to_db(self, save_test_results_to_db: bool):
        """Set the save_test_results_to_db attribute.

        Arguments:
        -----------
        save_test_results_to_db: bool
            If True, the test results are saved to the database.
        """
        self.save_test_results_to_db = save_test_results_to_db


    def get_save_test_results_to_db(self) -> bool:
        """Get the save_test_results_to_db attribute.

        Returns:
        -----------
        bool
            If True, the test results are saved to the database.
        """
        return self.save_test_results_to_db


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
        if self.save_test_results_to_db:
            self.save_results_to_db(file_results)
        return file_results


    def save_results_to_db(self, file_results: dict):
        """Save the test results to the database. Commits after saving the file output to the database table if connectable is Engine.
        
        Arguments:
        -----------
        file_results: dict
            Dict where key is the test file name and value is the test result. 
        """
        try:
            connectable = self.connectable
            connection = connectable.connect() if type(connectable) == Engine else connectable

            # Get test table columns
            test_table_columns = [column.name for column in self.table.columns]

            # Output format: Dict where key is the test file name and value is the test result.
            for filepath, output in file_results.items():

                # Get the next available BatchID
                batch_id = None
                if "BatchID" in test_table_columns:
                    batch_id = connection.execute(text(f"SELECT MAX(BatchID) + 1 FROM {self.table.fullname}")).scalar()
                    batch_id = 1 if batch_id is None else batch_id

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

                    # Add BatchID to the row
                    if "BatchID" in test_table_columns and "BatchID" not in output_columns:
                        row_dict["BatchID"] = batch_id

                    # Add the test file name to the row
                    if "TestFile" in test_table_columns and "TestFile" not in output_columns:
                        row_dict["TestFile"] = filepath

                    insert_list.append(row_dict)
                
                # Save the results to the database
                connection.execute(insert(self.table), insert_list)
                if type(connectable) == Engine:
                    connection.commit()

        except Exception as e:
            logger.error(f"Error saving test results to the database: {e}")
            raise e