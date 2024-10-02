# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for database tests related operations."""

from ahjo.operations.general.sqlfiles import deploy_sqlfiles
from ahjo.interface_methods import format_to_table
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
        start_time,
        end_time,
        test_name,
        issue,
        result
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
        file_results = deploy_sqlfiles(self.connectable, test_folder, "Running tests")
        if self.save_test_results_to_db:
            self.save_results_to_db(file_results)
        if display_output:
            self.display_test_results(file_results)
        return file_results


    def display_test_results(self, file_results: dict, cols_to_skip: list = ["start_time", "end_time"], 
            col_ordering: list = ["ID", "issue", "test_name", "result"]):
        """ Default method to display the test results.

        Arguments:
        -----------
        file_results: dict
            Dict where key is the test file name and value is the test result. 
        cols_to_skip: list
            List of column names to skip from the output.
        col_ordering: list
            List of column names to order the output.
        """

        # Default column name and value for the test results
        # This is used to count the number of tests passed
        result_col_name = "result"
        result_passed_str = "OK"
        n_files = len(file_results)

        for filepath, output in file_results.items():

            if n_files > 1:
                logger.info(f"Test file: {filepath}", extra={"record_class": "skip_db_record"})
                logger.info("", extra={"record_class": "skip_db_record"})

            output_columns = output[0]
            cols_to_skip_indices = [i for i, col in enumerate(output_columns) if col in cols_to_skip]
            new_rows = []
            result_col_exists = True if result_col_name in output_columns else False
            n_tests_passed = 0
            n_tests = len(output) - 1

            for row in output:

                new_row = []
                for col_i, col in enumerate(row):
                    if col_i in cols_to_skip_indices:
                        continue

                    if result_col_exists and col_i == output_columns.index(result_col_name) and col.lower() == result_passed_str.lower():
                        n_tests_passed += 1

                    new_row.append(col)

                # Reorder the columns if the col_ordering is given 
                # and all the columns are in the output_columns
                if isinstance(col_ordering, list) and all(col in output_columns for col in col_ordering):
                    new_row = []
                    for col in col_ordering:
                        try:
                            swap_indx = output_columns.index(col)
                        except Exception as e:
                            logger.error(f"Column '{col}' not found in the output columns: {output_columns}")
                            raise e
                        new_row.append(row[swap_indx])

                new_rows.append(new_row)

            # Header row to human friendly format
            if isinstance(new_rows[0], list):
                for header_i, col in enumerate(new_rows[0]):
                    if isinstance(col, str):
                        new_rows[0][header_i] = col.replace("_", " ").title()

            # Add final row with the number of tests passed
            if result_col_exists:
                new_rows.append(["", "", "TOTAL", f"{n_tests_passed}/{n_tests} PASSED"])

            logger.info(format_to_table(new_rows), extra={"record_class": "skip_db_record"})

            if result_col_exists and n_tests_passed != n_tests:
                n_failed_tests = n_tests - n_tests_passed
                tests_str = "tests" if n_failed_tests > 1 else "test"
                logger.warning(f"Warning: {n_failed_tests} {tests_str} failed!")
                logger.info("", extra={"record_class": "skip_db_record"})


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

                # Get the next available batch_id
                batch_id = None
                if "batch_id" in test_table_columns:
                    batch_id = connection.execute(text(f"SELECT MAX(batch_id) + 1 FROM {self.table.fullname}")).scalar()
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

                    # Add batch_id to the row
                    if "batch_id" in test_table_columns and "batch_id" not in output_columns:
                        row_dict["batch_id"] = batch_id

                    # Add the test file name to the row
                    if "test_file" in test_table_columns and "test_file" not in output_columns:
                        row_dict["test_file"] = filepath

                    insert_list.append(row_dict)
                
                # Save the results to the database
                connection.execute(insert(self.table), insert_list)
                if type(connectable) == Engine:
                    connection.commit()

        except Exception as e:
            logger.error(f"Error saving test results to the database: {e}")
            raise e