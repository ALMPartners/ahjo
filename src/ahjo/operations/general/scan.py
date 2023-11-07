# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

""" Module for scanning ahjo project files. """
import os
import re
import yaml
from datetime import datetime
from typing import Union
from logging import getLogger
from ahjo.operations.general.git_version import _get_all_files_in_staging_area, _get_all_files_in_working_directory

logger = getLogger("ahjo")

SCAN_RULES_WHITELIST = {"hetu"}
RULE_DESCRIPTIONS = {"hetu": "Finnish Personal Identity Number"}
SEARCH_PATTERNS = {
    "hetu": r"(0[1-9]|[1-2]\d|3[01])(0[1-9]|1[0-2])(\d\d)([-+A-FU-Y])(\d\d\d)([0-9A-FHJ-NPR-Y])"
}


def scan_project(filepaths_to_scan: list = ["^database/"], scan_staging_area: bool = False, 
    search_rules: Union[list, set] = SCAN_RULES_WHITELIST, log_additional_info: bool = True) -> dict:
    ''' Scan ahjo project git files using search rules. 
    
    Parameters
    ----------
    filepaths_to_scan
        List of file paths to scan. File paths are regular expressions.
    scan_staging_area   
        Scan files in git staging area instead of working directory.
    search_rules
        List of search rules to use in scan.
        Allowed search rules: 
            - hetu (Finnish Personal Identity Number)
    log_additional_info
        Log scan status info. This is disabled when running in quiet mode (e.g. pre-commit hook).
    
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
    '''
    
    # Validate parameters
    if not valid_search_rules(search_rules) or not valid_filepaths_to_scan(filepaths_to_scan):
        logger.warning("Scan aborted.")
        return None
    
    # Setup search patterns, load ignored matches, get files to scan and initialize result dictionary
    search_patterns = {key: SEARCH_PATTERNS[key] for key in search_rules} # select search patterns for search rules
    ignored_matches = load_ignored_matches() # load ignored matches from file
    git_files = _get_all_files_in_staging_area() if scan_staging_area else _get_all_files_in_working_directory()
    git_files = [git_file for git_file in git_files if git_file] # Remove possible empty strings from git_files
    matches = {} # dictionary containing matches for each file and search rule
    n_matches = 0 # number of matches

    # Scan each file
    for git_file in git_files:

        # Check if file path is in allowed file paths
        if not file_path_is_valid(git_file, filepaths_to_scan):
            continue

        try: # Load file content
            with open(git_file, "r") as f:
                file_content = f.read()
        except:
            logger.debug(f"Failed to load file: {git_file}")
            continue

        # Iterate through search rule patterns
        for search_rule_name, file_content_pattern in search_patterns.items():

            # Check for matches in file content using search rule pattern
            file_content_matches = [(m.start(0), m.end(0)) for m in re.finditer(file_content_pattern, file_content)]
            if len(file_content_matches) == 0:
                continue
                
            # Iterate through matches
            for file_content_match in file_content_matches: 

                match = file_content[file_content_match[0]:file_content_match[1]]

                # Check if file match string is in ignored matches
                if file_in_ignored_list(git_file, ignored_matches, match):
                    continue
                            
                # Validate match
                if search_rule_name == "hetu" and not is_hetu(match):
                    continue

                # Add match to results
                if git_file not in matches:
                    matches[git_file] = {}
                if search_rule_name not in matches[git_file]:
                    matches[git_file][search_rule_name] = []
                matches[git_file][search_rule_name].append(match)
                n_matches += 1

    log_scan_results(matches, n_matches)
    if log_additional_info: log_scan_status_info(n_matches > 0)

    return matches


def valid_search_rules(search_rules: Union[list, set]) -> list:
    """ Check if search rules are valid.

    Parameters
    ----------
    search_rules
        List of search rules to use in scan.

    Returns
    -------
    bool
        Are search rules valid or not?
    """
    if not isinstance(search_rules, (list, set)):
        logger.warning(f"Invalid type for search_rules: {type(search_rules)}")
        return False
    if len(search_rules) == 0:
        logger.warning("No search rules specified.")
        return False
    for search_rule in search_rules:
        if search_rule not in SCAN_RULES_WHITELIST:
            logger.warning("Invalid search rule: " + search_rule + ". Use one of the following search rules: " + ','.join(SCAN_RULES_WHITELIST) + ".")
            return False
    return True


def valid_filepaths_to_scan(filepaths_to_scan):
    """ Check if file paths to scan are valid.

    Parameters
    ----------
    filepaths_to_scan
        List of file paths to scan. File paths are regular expressions.
    
    Returns
    -------
    bool
        Are file paths to scan valid or not?
    """
    if not isinstance(filepaths_to_scan, list): 
        logger.warning(f"Invalid type for filepaths_to_scan: {type(filepaths_to_scan)}")
        return False
    if len(filepaths_to_scan) == 0:
        logger.warning("No file paths specified.")
        return False
    for f_path in filepaths_to_scan:
        if not isinstance(f_path, str):
            logger.warning(f"Invalid type for file path: {type(f_path)}")
            return False
    return True


def file_path_is_valid(file_path: str, allowed_filepaths: list) -> bool:
    """ Check if file path is in allowed file paths. 
    
    Parameters
    ----------
    file_path
        File path to check.
    allowed_filepaths
        List of allowed file paths. File paths are regular expressions.

    Returns
    -------
    bool
        Is file path in allowed file paths or not?
    """
    if len(file_path) == 0: return False
    for scan_filepath_pattern in allowed_filepaths:
        if re.search(scan_filepath_pattern, file_path):
            return True
    return False


def is_hetu(match: str) -> bool:
    """ Check if match is valid hetu (Finnish Personal Identity Number).

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
        hetu_date = datetime.strptime(birth_day + "-" + birth_month + "-" + birth_year, '%d-%m-%Y')
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


def file_in_ignored_list(file: str, ignored_matches: dict, match: str) -> bool:
    """ Check if file content match is in ignored matches. 
    
    Parameters
    ----------
    file
        File path.
    ignored_matches
        Dictionary containing ignored matches for each file. 
    match
        Match to check if it is in ignored matches.
    
    Returns
    -------
    bool
        Is file match in ignored matches or not? 
    """
    if file in ignored_matches:
        for ignored_match in ignored_matches[file]:
            if ignored_match == match:
                return True
    return False           


def log_scan_results(matches: dict, n_matches: int) -> None:
    """ Log scan results. 
    
    Parameters
    ----------
    matches
        Dictionary containing matches for each file and search rule.
    n_matches
        Number of matches.
    """
    len_matches = len(matches)
    if len_matches > 0:
        logger.info("Scan completed. Found " + str(n_matches) + " match" + ("es" if n_matches > 1 else "") + ":")
        logger.info("")
        for file in matches:
            logger.info(f"  File: {file}")
            for search_rule in matches[file]:
                logger.info(f"  Search rule: {RULE_DESCRIPTIONS[search_rule]}")
                logger.info(f"  Matches:")
                for match in matches[file][search_rule]:
                    logger.info(f"      {match}")
                logger.info("")


def log_scan_status_info(matches_found: bool) -> None:
    """ Log scan status info. 
     
    Parameters
    ----------
    matches_found
        Are there any matches?     
    """
    if matches_found:
        logger.info("""If you want to ignore a match, add it to the ahjo_scan_ignore.yaml file.""")
        logger.info("")
    else:
        logger.info("Scan completed.")
        logger.info("No matches found.")
        logger.info("")


def load_ignored_matches(file_path: str = "ahjo_scan_ignore.yaml") -> dict:
    """ Load ignored matches from file. Matches in this file are ignored in scan results.
    
    Parameters
    ----------

    file_path
        Path to the file containing ignored matches.
        The file should be in the following format: 

        files:
            - file_path: <file_path>
              matches:
                - <match>
                - <match>
            - file_path: <file_path>
              matches:
                - <match>


    """
    ignored_matches = {}
    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            with open(file_path, 'r') as stream:
                ignored_matches_yaml = yaml.load(stream, Loader=yaml.CLoader)["files"]
            for ignored_item in ignored_matches_yaml:
                file_path = ignored_item["file_path"]
                ignored_matches[file_path] = []
                for match in ignored_item["matches"]:
                    ignored_matches[file_path].append(match)
        except Exception as e:
            logger.warning(f"Failed to load ignored matches from {file_path}.")
            logger.warning(e)
            pass
    else: # Create example ignore yaml file if it does not exist
        with open(file_path, 'w') as stream:
            yaml.dump({
                "files": [
                    {
                        "file_path": "database/data/example.sql",
                        "matches": [
                            "example_pattern_1",
                            "example_pattern_2"
                        ]
                    },
                    {
                        "file_path": "database/data/example_2.sql",
                        "matches": [
                            "example_pattern_3",
                        ]
                    }
                ]
            }, stream, default_flow_style=False)

    return ignored_matches