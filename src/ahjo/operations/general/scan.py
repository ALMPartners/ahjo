# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

""" """
import os
import re
import yaml
from datetime import datetime
from typing import Union
from logging import getLogger
from ahjo.operations.general.git_version import _get_all_files_in_staging_area, _get_all_files_in_working_directory
from dateutil.parser import parse

logger = getLogger("ahjo")

# Allowed search rules
SCAN_RULES_WHITELIST = {
    "hetu" # Finnish Personal Identity Number
}

# Search patterns for search rules
SEARCH_PATTERNS = {
    "hetu": r"(0[1-9]|[1-2]\d|3[01])(0[1-9]|1[0-2])(\d\d)([-+A-FU-Y])(\d\d\d)([0-9A-FHJ-NPR-Y])"
}


def scan_project(filepaths_to_scan: list = ["^database/"], scan_staging_area: bool = False, search_rules: Union[list, set] = SCAN_RULES_WHITELIST):
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
    
    # Setup search patterns, load ignored matches, get files to scan and initialize result dictionary
    valid_search_rules = validate_search_rules(search_rules)
    if len(valid_search_rules) == 0:
        return {}
    search_patterns = {key: SEARCH_PATTERNS[key] for key in valid_search_rules} # select search patterns for search rules
    ignored_matches = load_ignored_matches() # load ignored matches from file
    git_files = _get_all_files_in_staging_area() if scan_staging_area else _get_all_files_in_working_directory()
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
            logger.warning(f"Failed to load file: {git_file}")
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

    return matches


def validate_search_rules(search_rules: Union[list, set]):
    """ Check if search rules are valid.

    Parameters
    ----------
    search_rules
        List of search rules to use in scan.

    Returns
    -------
    search_rules_filtered
        List of valid search rules.
    """
    search_rules_filtered = []
    if not isinstance(search_rules, (list, set)):
        raise TypeError(f"Invalid type for search_rules: {type(search_rules)}")
    if len(search_rules) == 0:
        raise ValueError("No search rules specified.")
    for search_rule in search_rules:
        if search_rule not in SCAN_RULES_WHITELIST:
            logger.warning(f"{search_rule} is not a valid search rule. Skipping it.")
            continue
        search_rules_filtered.append(search_rule)
    if len(search_rules_filtered) == 0:
        logger.warning("No valid search rules specified. Use one of the following search rules: " + ','.join(SCAN_RULES_WHITELIST) + ".")
    return search_rules_filtered


def file_path_is_valid(file_path: str, allowed_filepaths: list):
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
    for scan_filepath_pattern in allowed_filepaths:
        if re.search(scan_filepath_pattern, file_path):
            return True
    return False


def is_hetu(match: str):
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
        hetu_date = parse(birth_day + "." + birth_month + "." + birth_year, dayfirst=True)
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


def file_in_ignored_list(file: str, ignored_matches: dict, match: str):
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


def log_scan_results(matches: dict, n_matches: int):
    """ Log scan results. 
    
    Parameters
    ----------
    matches
        Dictionary containing matches for each file and search rule.
    n_matches
        Number of matches.
    """
    logger.info("Ahjo scan completed.")
    len_matches = len(matches)
    if len_matches > 0:
        logger.info("Found " + str(n_matches) + " match" + ("es" if n_matches > 1 else "") + ":")
        logger.info("")
        for file in matches:
            logger.info(f"  File: {file}")
            for search_rule in matches[file]:
                logger.info(f"  Search rule: {search_rule}")
                logger.info(f"  Matches:")
                for match in matches[file][search_rule]:
                    logger.info(f"      {match}")
                logger.info("")
        logger.info("""If you want to ignore a match, add it to the ahjo_scan_ignore.yaml file.""")
        logger.info("")
    else:
        logger.info("No matches found.")


def load_ignored_matches(file_path: str = "ahjo_scan_ignore.yaml"):
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
    else: # Create commented example ignore yaml file if it does not exist
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