# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for scanning ahjo project files."""
import os
import re
import yaml
from datetime import datetime
from logging import getLogger
from ahjo.operations.general.git_version import (
    _get_files_in_staging_area,
    _get_files_in_working_directory,
)

logger = getLogger("ahjo")

DEFAULT_SCAN_RULES = [{"name": "hetu", "filepath": "."}]
SCAN_RULES_WHITELIST = {"hetu", "email", "sql_insert", "sql_object_modification"}
RULE_DESCRIPTIONS = {
    "hetu": "Finnish Personal Identity Number",
    "email": "Email address",
    "sql_insert": "Database insert (SQL Server)",
    "sql_object_modification": "Database object modification (SQL Server)",
    "alembic_table_modification": "Database table modification (Alembic)",
}
SEARCH_PATTERNS = {
    "hetu": r"(0[1-9]|[1-2]\d|3[01])(0[1-9]|1[0-2])(\d\d)([-+A-FU-Y])(\d\d\d)([0-9A-FHJ-NPR-Y])",
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b",
    "sql_insert": r"(?i:INSERT((\s)+INTO)?)(\s)+(\[)?(SCHEMAS_PLACEHOLDER)(\])?(\s)*[.](\s)*(\[)?(TABLES_PLACEHOLDER)(\])?(\s)*\(.+\)",
    "sql_object_modification": r"(?i:(DROP|CREATE|ALTER)(\s)+(OBJECT_TYPES_PLACEHOLDER))(\s)+(\[)?(SCHEMAS_PLACEHOLDER)(\])?(\s)*[.](\s)*(\[)?(OBJECTS_PLACEHOLDER)(\]|\s)",
    "alembic_table_modification": r'(add_column|alter_column|create_primary_key|create_table|create_unique_constraint|drop_column|drop_constraint|drop_table|rename_table)\(.*schema(\s)*=(\s)*[\'"](SCHEMAS_PLACEHOLDER)[\'"].*\)',
}


class AhjoScan:
    """Class for scanning ahjo project files.

    Attributes
    ----------
        scan_staging_area
            Scan files in git staging area instead of working directory.
        search_rules
            List of search rules to use in scan.
            Allowed search rules:
                - hetu (Finnish Personal Identity Number)
        log_additional_info
            Log scan status info. This is disabled when running in quiet mode (e.g. pre-commit hook).
        ignore_config_path
            Path to the file containing ignored results.
    """

    def __init__(
        self,
        scan_staging_area: bool = False,
        search_rules: list = DEFAULT_SCAN_RULES,
        log_additional_info: bool = True,
        ignore_config_path: str = "ahjo_scan_ignore.yaml",
        scan_rules_file: str = "ahjo_scan_rules.yaml",
        add_results_to_ignore: bool = False,
    ):
        """Constructor for AhjoScan class.

        Parameters
        ----------
        scan_staging_area
            Scan files in git staging area instead of working directory.
        search_rules
            List of search rules to use in scan.
            Allowed search rules:
                - hetu (Finnish Personal Identity Number)
        log_additional_info
            Log scan status info. This is disabled when running in quiet mode (e.g. pre-commit hook).
        ignore_config_path
            Path to the file containing ignored results.
        add_results_to_ignore
            Add found scan results to ignore config file.
        """
        self.scan_staging_area = scan_staging_area
        self.search_rules = search_rules
        self.log_additional_info = log_additional_info
        self.ignore_config_path = ignore_config_path
        self.scan_rules_file = scan_rules_file
        self.add_results_to_ignore = add_results_to_ignore
        self.matches = None

    def initialize_scan_config(self):
        """Initialize config files for scan rules and ignored scan results.

        Parameters
        ----------
        scan_ignore_file
            Path to the file containing ignored matches.
        scan_rules_file
            Path to the file containing scan rules.
        """
        scan_ignore_file = self.ignore_config_path
        scan_rules_file = self.scan_rules_file
        scan_ignore_file_exists = os.path.exists(scan_ignore_file)
        scan_rules_file_exists = os.path.exists(scan_rules_file)

        if scan_ignore_file_exists:
            logger.warning(
                f"Config file for ignored scan results already exist: {scan_ignore_file}. Remove this file if you want to initialize a new one."
            )
        if scan_rules_file_exists:
            logger.warning(
                f"Config file for scan rules already exist: {scan_rules_file}. Remove this file if you want to initialize a new one."
            )
        if scan_ignore_file_exists and scan_rules_file_exists:
            logger.warning("Initialization aborted.")
            return

        if not scan_rules_file_exists:
            with open(scan_rules_file, "w") as stream:
                yaml.dump(
                    [
                        {
                            "name": "hetu",
                            "filepath": ["database/", "alembic/versions/"],
                        },
                        {
                            "name": "email",
                            "filepath": ["database/"],
                        },
                        {
                            "name": "sql_object_modification",
                            "filepath": ["database/"],
                            "object_types": [
                                "PROCEDURE",
                                "FUNCTION",
                                "VIEW",
                                "TRIGGER",
                                "TABLE",
                                "TYPE",
                                "ASSEMBLY",
                            ],
                            "schemas": [""],
                            "objects": [""],
                        },
                        {
                            "name": "sql_insert",
                            "filepath": ["database/"],
                            "schemas": [""],
                            "tables": [""],
                        },
                        {
                            "name": "alembic_table_modification",
                            "filepath": ["alembic/versions/"],
                            "schemas": [""],
                        },
                    ],
                    stream,
                    default_flow_style=False,
                    sort_keys=False,
                )
            logger.info(f"Config file for scan rules initialized: {scan_rules_file}")

        if not scan_ignore_file_exists:
            with open(scan_ignore_file, "w") as stream:
                yaml.dump(
                    [
                        {
                            "file_path": "database/data/example.sql",
                            "matches": ["example_match_1", "example_match_2"],
                        },
                        {
                            "file_path": "database/data/example_2.sql",
                            "rules": [
                                "example_rule_id_1",
                            ],
                        },
                    ],
                    stream,
                    default_flow_style=False,
                    sort_keys=False,
                )
            logger.info(
                f"Config file for ignored scan results initialized: {scan_ignore_file}"
            )

    def scan_project(self) -> dict:
        """Scan ahjo project git files using search rules.

        Returns
        -------
        matches
            Dictionary containing matches for each file and search rule.
            Example:
            {
                "database/data/employee.sql": {
                    "hetu": [
                        "230218A232C"
                    ]
                }
            }
        """

        start_time = datetime.now()

        # Validate parameters
        if not self.valid_search_rules():
            logger.warning("Scan aborted.")
            return None

        # Collect filepaths to scan
        filepaths = []
        for rule in self.search_rules:
            rule_filepath = rule.get("filepath")
            if isinstance(rule_filepath, str):
                filepaths.append(rule_filepath)
            elif isinstance(rule_filepath, list):
                filepaths.extend(rule_filepath)
            else:
                filepaths.append(".")  # scan all files if no file path is specified

        if self.scan_staging_area:
            git_files = (
                _get_files_in_staging_area(filepaths)
                if len(filepaths) > 0
                else _get_files_in_staging_area()
            )
        else:
            git_files = (
                _get_files_in_working_directory(filepaths)
                if len(filepaths) > 0
                else _get_files_in_working_directory()
            )

        git_files = [
            git_file for git_file in git_files if git_file
        ]  # Remove possible empty strings from git_files
        ignored_items = self.load_ignored_items()
        matches = {}  # dictionary containing matches for each file and search rule
        n_matches = 0  # number of matches
        n_ignored = 0  # number of ignored matches/rules
        self.add_placeholders_to_patterns()

        # Scan each file
        for git_file in git_files:

            try:  # Load file content
                with open(git_file, "r") as f:
                    file_content = f.read()
            except:
                logger.debug(f"Failed to load file: {git_file}")
                continue

            # Iterate through search rules
            for search_rule in self.search_rules:

                search_rule_name = search_rule.get("name")

                # Check if file is in ignored rules
                if self.file_in_ignored_list(
                    git_file,
                    ignored_items,
                    ignore_type="rules",
                    rule_name=search_rule_name,
                ):
                    n_ignored += 1
                    continue

                # Check if git_file is in search rule file path
                rule_filepaths = search_rule.get("filepath", ".")
                if isinstance(rule_filepaths, str):
                    rule_filepaths = [rule_filepaths]
                if not any(
                    [
                        re.search(rule_filepath, git_file)
                        for rule_filepath in rule_filepaths
                    ]
                ):
                    continue

                # Get search rule pattern
                search_rule_pattern = search_rule.get("pattern")  # Custom search
                if not search_rule_pattern:
                    search_rule_pattern = SEARCH_PATTERNS.get(search_rule_name)
                if not search_rule_pattern:
                    logger.warning(
                        f"Invalid search rule: {search_rule_name}. Search rule pattern not found."
                    )
                    continue

                # Check for matches in file content using search rule pattern
                file_content_matches = [
                    (m.start(0), m.end(0))
                    for m in re.finditer(search_rule_pattern, file_content)
                ]
                if len(file_content_matches) == 0:
                    continue

                # Iterate through matches
                for file_content_match in file_content_matches:

                    match = file_content[file_content_match[0] : file_content_match[1]]

                    # Check if file match string is in ignored matches
                    if self.file_in_ignored_list(
                        git_file,
                        ignored_items,
                        ignore_type="matches",
                        match=match.strip(),
                    ):
                        n_ignored += 1
                        continue

                    # Validate match
                    if search_rule_name == "hetu" and not self.is_hetu(match):
                        continue

                    # Add match to results
                    if git_file not in matches:
                        matches[git_file] = {}
                    if search_rule_name not in matches[git_file]:
                        matches[git_file][search_rule_name] = []
                    matches[git_file][search_rule_name].append(match)
                    n_matches += 1

        self.log_scan_results(
            matches, n_matches, str(datetime.now() - start_time), n_ignored
        )
        matches_found = n_matches > 0
        if self.log_additional_info:
            self.log_scan_status_info(matches_found)

        if self.add_results_to_ignore and matches_found:
            self.add_results_to_ignore_list(matches, ignored_items)

        return matches

    def valid_search_rules(self) -> list:
        """Check if search rules are valid.

        Returns
        -------
        bool
            Are search rules valid or not?
        """
        search_rules = self.search_rules
        if not isinstance(search_rules, list):
            logger.warning(f"Invalid type for search_rules: {type(search_rules)}")
            return False
        if len(search_rules) == 0:
            logger.warning("No search rules specified.")
            return False
        return True

    def add_placeholders_to_patterns(self):
        """Add placeholders to search rule patterns."""
        for rule_indx, search_rule in enumerate(self.search_rules):

            search_rule_name = search_rule.get("name")
            if search_rule_name not in [
                "sql_insert",
                "sql_object_modification",
                "alembic_table_modification",
            ]:
                continue

            schemas_placeholder = search_rule.get("schemas", r".\S+")
            schemas_placeholder = (
                "|".join(schemas_placeholder)
                if isinstance(schemas_placeholder, list)
                else schemas_placeholder
            )

            if search_rule_name == "sql_insert":
                tables_placeholder = search_rule.get("tables", r".\S+")
                search_pattern = (
                    SEARCH_PATTERNS.get(search_rule_name)
                    .replace("SCHEMAS_PLACEHOLDER", schemas_placeholder)
                    .replace(
                        "TABLES_PLACEHOLDER",
                        (
                            "|".join(tables_placeholder)
                            if isinstance(tables_placeholder, list)
                            else tables_placeholder
                        ),
                    )
                )

            if search_rule_name == "sql_object_modification":
                object_types_placeholder = search_rule.get(
                    "object_types",
                    [
                        "PROCEDURE",
                        "FUNCTION",
                        "VIEW",
                        "TRIGGER",
                        "TABLE",
                        "TYPE",
                        "ASSEMBLY",
                    ],
                )
                objects_placeholder = search_rule.get("objects", r".\S+")
                search_pattern = (
                    SEARCH_PATTERNS.get(search_rule_name)
                    .replace(
                        "OBJECT_TYPES_PLACEHOLDER",
                        (
                            "|".join(object_types_placeholder)
                            if isinstance(object_types_placeholder, list)
                            else object_types_placeholder
                        ),
                    )
                    .replace("SCHEMAS_PLACEHOLDER", schemas_placeholder)
                    .replace(
                        "OBJECTS_PLACEHOLDER",
                        (
                            "|".join(objects_placeholder)
                            if isinstance(objects_placeholder, list)
                            else objects_placeholder
                        ),
                    )
                )

            if search_rule_name == "alembic_table_modification":
                search_pattern = SEARCH_PATTERNS.get(search_rule_name).replace(
                    "SCHEMAS_PLACEHOLDER", schemas_placeholder
                )

            self.search_rules[rule_indx]["pattern"] = search_pattern

    def is_hetu(self, match: str) -> bool:
        """Check if match is valid hetu (Finnish Personal Identity Number).

        Parameters
        ----------
        match
            Match to validate.

        Returns
        -------
        bool
            Is match valid hetu or not?

        ToDo:
            tarkistusmerkin validointi? (https://www.tuomas.salste.net/doc/tunnus/henkilotunnus.html)
        """

        if len(match) != 11:
            return False

        birth_day = match[0:2]
        birth_month = match[2:4]
        hetu_mark = match[6]
        hetu_year = match[4:6]

        # Check if mark is valid
        if hetu_mark in ["+"]:
            birth_year = "18" + hetu_year
        elif hetu_mark in ["-", "Y", "X", "W", "V", "U"]:
            birth_year = "19" + hetu_year
        elif hetu_mark in ["A", "B", "C", "D", "E", "F"]:
            birth_year = "20" + hetu_year
        else:
            return False

        # Check if date is valid
        try:
            hetu_date = datetime.strptime(
                birth_day + "-" + birth_month + "-" + birth_year, "%d-%m-%Y"
            )
        except:
            return False

        # Check if date is not in the future
        present = datetime.now()
        if hetu_date.date() > present.date():
            return False

        # Check if birth year is not too old
        if hetu_date.year < 1850:
            return False

        return True

    def file_in_ignored_list(
        self,
        file: str,
        ignored_items: dict,
        ignore_type=None,
        match: str = None,
        rule_name=None,
    ) -> bool:
        """Check if file content match is in ignored matches.

        Parameters
        ----------
        file
            File path.
        ignored_items
            Dictionary containing ignored matches or rules for each file.
        ignore_type
            Type of ignored item. Allowed values: "rules", "matches"
        match
            Match to check if it is in ignored matches.
        rule_name
            Rule name to check if it is in ignored matches.

        Returns
        -------
        bool
            Is file match in ignored items or not?
        """
        if file in ignored_items:
            if ignore_type in ignored_items[file]:
                for ignored_item in ignored_items[file][ignore_type]:
                    if ignore_type == "rules":
                        if ignored_item == rule_name:
                            return True
                    if ignore_type == "matches":
                        if match in ignored_item:
                            return True
        return False

    def log_scan_results(
        self, matches: dict, n_matches: int, scan_time: str, n_ignored: int
    ) -> None:
        """Log scan results.

        Parameters
        ----------
        matches
            Dictionary containing matches for each file and search rule.
        n_matches
            Number of matches.
        scan_time
            Scan time ("HH:MM:SS.ms")
        n_ignored
            Number of ignored matches/rules.
        """
        len_matches = len(matches)
        if len_matches > 0:
            logger.info("")
            logger.info("Scan completed")
            logger.info("---------------------------------")
            logger.info("Matches:           " + str(n_matches))
            if n_ignored > 0:
                logger.info(f"Ignored matches:   {n_ignored}")
            logger.info("Ellapsed time:     " + scan_time)
            logger.info("---------------------------------")
            logger.info("")
            logger.info("Results:")
            logger.info("")

            for file in matches:
                logger.info(f"  File: {file}")
                for search_rule in matches[file]:
                    search_rule_str = (
                        search_rule
                        if search_rule not in RULE_DESCRIPTIONS
                        else RULE_DESCRIPTIONS[search_rule]
                    )
                    logger.info(f"  Search rule: {search_rule_str}")
                    logger.info(f"  Matches:")
                    for match in matches[file][search_rule]:
                        logger.info(f"      {match.rstrip()}")
                    logger.info("")

    def log_scan_status_info(self, matches_found: bool) -> None:
        """Log scan status info.

        Parameters
        ----------
        matches_found
            Are there any matches?
        """
        if matches_found:
            logger.info(
                """If you want to ignore a match, add it to the ahjo_scan_ignore.yaml file."""
            )
            logger.info("")
        else:
            logger.info("Scan completed.")
            logger.info("No matches found.")
            logger.info("")

    def load_ignored_items(self) -> dict:
        """Load ignored items from file. Matches or rules in this file are ignored in scan results."""
        file_path = self.ignore_config_path
        ignored_items = {}
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                with open(file_path, "r") as stream:
                    ignored_items_yaml = yaml.load(stream, Loader=yaml.CLoader)

                if ignored_items_yaml is not None and len(ignored_items_yaml) > 0:
                    for ignored_item in ignored_items_yaml:

                        file_path = ignored_item["file_path"]
                        ignored_items[file_path] = {}

                        if "matches" in ignored_item:
                            ignored_items[file_path]["matches"] = []
                            for match in ignored_item["matches"]:
                                ignored_items[file_path]["matches"].append(match)
                        if "rules" in ignored_item:
                            ignored_items[file_path]["rules"] = []
                            for rule in ignored_item["rules"]:
                                ignored_items[file_path]["rules"].append(rule)

            except Exception as e:
                logger.warning(f"Failed to load ignored matches from {file_path}.")
                logger.warning(e)
                pass
        else:
            logger.debug(f"Ignored matches file not found: {file_path}")

        return ignored_items

    def add_results_to_ignore_list(self, matches: dict, ignored_items: dict) -> None:
        """Add scan results to ignored list.

        Parameters
        ----------
        matches
            Dictionary containing matches for each file and search rule.
        ignore_config_path
            Path to the file containing ignored results.
        """
        for file in matches:
            if file not in ignored_items:
                ignored_items[file] = {}
                ignored_items[file]["matches"] = []
            for search_rule in matches[file]:
                for match in matches[file][search_rule]:
                    if match not in ignored_items[file]["matches"]:
                        ignored_items[file]["matches"].append(match.strip())
        with open(self.ignore_config_path, "w") as stream:
            yaml.dump(
                [
                    {**{"file_path": file}, **ignored_items[file]}
                    for file in ignored_items
                ],
                stream,
                default_flow_style=False,
                sort_keys=False,
            )
        logger.info(f"Results added to ignored list: {self.ignore_config_path}")
