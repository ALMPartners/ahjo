# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Password information handling."""
import getpass
from base64 import b64decode, b64encode
from logging import getLogger
from pathlib import Path
from typing import Tuple, Union

logger = getLogger("ahjo")


def obfuscate_credentials(credentials: Tuple[str, str]) -> Tuple[str, str]:
    """Not secure encryption of credentials.
    At least it is not in plain text.
    """
    username, password = credentials
    obfuscated_password = b64encode(password.encode()).decode()
    return username, obfuscated_password


def deobfuscate_credentials(credentials: Tuple[str, str]) -> Tuple[str, str]:
    """Reverse of obfuscate_credentials."""
    username, obfuscated_password = credentials
    password = b64decode(obfuscated_password.encode()).decode()
    return username, password


def lookup_from_file(key: str, filename: str) -> Union[str, None]:
    """Return value from file.

    In cases where key exists but value doesn't (case: trusted connection), returns empty string.
    """
    if not Path(filename).is_file():
        return None
    with open(filename, "r") as f:
        for line in f:
            try:
                linekey, val = line.split("=", 1)
                if linekey == key:
                    return val
            except:
                return ""
    return None


def store_to_file(key: str, val: str, filename: str):
    """Write key and value pairs to file.
    If file directory does not exists, create directory before writing.
    """
    if not Path(filename).parent.exists():
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "a+") as f:
        f.writelines(str(key) + "=" + str(val))


def get_credentials(
    usrn_file_path: str = None,
    pw_file_path: str = None,
    cred_key: str = "cred",
    usrn_prompt: str = "Username: ",
    pw_prompt: str = "Password: ",
) -> Tuple[str, str]:
    """Retrieves credentials or asks for them.
    The credentials are stored in a global variable.

    Arguments
    ---------
    usrn_file_path
        The username file path or None for no storing.
    pw_file_path
        The password file path or None for no storing.
    cred_file_path
        The path to the credentials file.
        If None, the credentials are not stored.
    usrn_prompt
        How the username is asked.
    pw_prompt
        How the password is asked.
        If None, password is not asked from user.

    Returns
    -------
    Tuple[str, str]
        The username and the password in a tuple.
    """
    global cred_dict

    if "cred_dict" not in globals():
        cred_dict = {}

    if cred_key not in cred_dict:
        if usrn_file_path is not None and pw_file_path is not None:
            username = lookup_from_file(cred_key, usrn_file_path)
            password = lookup_from_file(cred_key, pw_file_path)
            if username is not None and password is not None:
                pass
            else:
                logger.info("Credentials are not yet defined.")
                logger.info(
                    f"The credentials will be stored in files {usrn_file_path} and {pw_file_path}"
                )
                username = input(usrn_prompt)
                new_password = getpass.getpass(pw_prompt) if pw_prompt else ""
                username, password = obfuscate_credentials((username, new_password))
                store_to_file(cred_key, username, usrn_file_path)
                store_to_file(cred_key, password, pw_file_path)
        else:
            username = input(usrn_prompt)
            new_password = getpass.getpass(pw_prompt) if pw_prompt else ""
            username, password = obfuscate_credentials((username, new_password))
        cred_dict[cred_key] = (username, password)
    return deobfuscate_credentials(cred_dict[cred_key])
