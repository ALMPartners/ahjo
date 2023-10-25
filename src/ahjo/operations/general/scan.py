# Ahjo - Database deployment framework
#
# Copyright 2019 - 2023 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

""" """
import os
import re
import yaml
import ahjo
from datetime import datetime
from typing import Union
from logging import getLogger
from logging.config import fileConfig
from ahjo.operations.general.git_version import _get_git_commit_info
from subprocess import check_output
from dateutil.parser import parse

logger = getLogger("ahjo")
fileConfig(os.path.join(os.path.dirname(ahjo.__file__), 'resources/logger.ini'))

# Allowed search rules
SCAN_RULES_WHITELIST = {
    "hetu" # Finnish Personal Identity Number
}

# Search patterns for search rules
SEARCH_PATTERNS = {
    "hetu": r"(0[1-9]|[1-2]\d|3[01])(0[1-9]|1[0-2])(\d\d)([-+A-FU-Y])(\d\d\d)([0-9A-FHJ-NPR-Y])"
}


def scan_project(filepaths_to_scan: list = ["^database/"], scan_staging_area: bool = False, search_rules: Union[list, set] = SCAN_RULES_WHITELIST):
    """ Scan ahjo project git files using search rules. 
    
    Parameters
    ----------
    filepaths_to_scan
        List of file paths to scan. 
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
    """

    # Setup search rules and load ignored matches
    search_rules_set = set(search_rules).intersection(SCAN_RULES_WHITELIST) # filter out invalid search rules
    search_patterns = {key: SEARCH_PATTERNS[key] for key in search_rules_set} # select search patterns for search rules
    ignored_matches = load_ignored_matches() # load ignored matches from file

    # Get files to scan
    if scan_staging_area:
        git_command = ["git", "diff", "--cached", "--name-only"] # all files in staging area
    else:
        _, commit = _get_git_commit_info()
        git_command = ["git", "ls-tree", "-r", "--name-only", commit] # all files in working directory
    git_files = check_output(git_command).decode("utf-8").strip().split("\n")

    matches = {}

    # Scan each file
    for git_file in git_files:

        # Iterate through file paths to scan
        for scan_filepath_pattern in filepaths_to_scan:

            # Check if file path is valid
            git_filepath_valid = re.search(scan_filepath_pattern, git_file)

            if git_filepath_valid:

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

                    # Match(es) found
                    if len(file_content_matches) > 0:
                        for file_content_match in file_content_matches: # Iterate through matches

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

    log_scan_results(matches)

    return matches


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


def log_scan_results(matches: dict):
    """ Log scan results. 
    
    Parameters
    ----------
    matches
        Dictionary containing matches for each file and search rule.

    """
    logger.info("Ahjo scan completed.")
    len_matches = len(matches)
    if len_matches > 0:
        logger.info("Found " + str(len_matches) + " match" + ("es" if len_matches > 1 else "") + ":")
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
    return ignored_matches