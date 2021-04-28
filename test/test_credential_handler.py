from base64 import b64encode
from os import remove

import pytest

import ahjo.credential_handler as ahjo


def obfuscate(stng):
    return b64encode(stng.encode()).decode()


@pytest.fixture(scope="function")
def execute_get_credentials_with_varying_input(tmp_path, monkeypatch):
    """First, reset global variable of Ahjo's credential_handler module.
        If this is not done, tests will affect one another.
    Second, create username/password files with given content and store
        file paths to list created_records.
    Third, set username/password input with monkeypatch.
    Fourth, execute ahjo.get_credentials with created username/password file
        paths as parameters (None if no file created).
    Fifth, reset global variable of Ahjo's credential_handler module.
        If this is not done, tests will affect one another.
    Finally, delete created username/password files.
    """
    # reset global variable
    ahjo.cred_dict = {}

    created_records = []

    def get_credentials(usrn_file_name, usrn_file_content, pw_file_name, pw_file_content, usrn_input, pw_input, ask_pw=True):
        # create username file if file name and content given
        usrn_file_path = None
        if usrn_file_name and usrn_file_content is not None:
            usrn_file_path = tmp_path / usrn_file_name
            usrn_file_path.write_text(
                f"cred={usrn_file_content}", encoding="utf-8")
            created_records.append(str(usrn_file_path))
        # create password file if file name and content given
        pw_file_path = None
        if pw_file_name and pw_file_content is not None:
            pw_file_path = tmp_path / pw_file_name
            pw_file_path.write_text(
                f"cred={pw_file_content}", encoding="utf-8")
            created_records.append(str(pw_file_path))
        # monkeypatch username and password input
        monkeypatch.setattr('builtins.input', lambda x: usrn_input)
        monkeypatch.setattr('getpass.getpass', lambda x: pw_input)
        if ask_pw:
            return ahjo.get_credentials(usrn_file_path=usrn_file_path, pw_file_path=pw_file_path)
        else:
            return ahjo.get_credentials(usrn_file_path=usrn_file_path, pw_file_path=pw_file_path, pw_prompt=None)

    yield get_credentials

    # reset global variable
    ahjo.cred_dict = {}

    # executed despite of result
    for record in created_records:
        remove(record)


def test_credentials_should_be_read_from_file_when_both_paths_given(execute_get_credentials_with_varying_input):
    """Both files given - read credentials from files.
    input: file_path, "cred=USER1", file_path, "cred=PASSWORD1", None, None
    output: ("USER1", "PASSWORD1")
    """
    testinput = ("usrn1.txt", "USER1", "pw1.txt",
                 obfuscate("PASSWORD1"), None, None)
    assert ("USER1", "PASSWORD1") == execute_get_credentials_with_varying_input(
        *testinput)


def test_credentials_should_be_asked_when_username_file_not_given(execute_get_credentials_with_varying_input):
    """Username file not given - ask credentials from user.
    input: None, None, file_path, "cred=PASSWORD", "USER2", "PASSWORD2"
    output: ("USER2", "PASSWORD2")
    """
    testinput = (None, None, "pw2.txt", obfuscate(
        "PASSWORD"), "USER2", "PASSWORD2")
    assert ("USER2", "PASSWORD2") == execute_get_credentials_with_varying_input(
        *testinput)


def test_credentials_should_be_asked_when_password_file_not_given(execute_get_credentials_with_varying_input):
    """Password file not given - ask credentials from user.
    input: file_path, "cred=USER", None, None, "USER3", "PASSWORD3"
    output: ("USER3", "PASSWORD3")
    """
    testinput = ("usrn3.txt", "USER", None, None, "USER3", "PASSWORD3")
    assert ("USER3", "PASSWORD3") == execute_get_credentials_with_varying_input(
        *testinput)


def test_credentials_should_be_asked_when_both_files_not_given(execute_get_credentials_with_varying_input):
    """Username and password files not given - ask credentials from user.
    input: None, None, None, None, "USER4", "PASSWORD4"
    output: ("USER4", "PASSWORD4")
    """
    testinput = (None, None, None, None, "USER4", "PASSWORD4")
    assert ("USER4", "PASSWORD4") == execute_get_credentials_with_varying_input(
        *testinput)


def test_windows_authentication_from_files_should_return_empty_strings(execute_get_credentials_with_varying_input):
    """Windows authentication from files - return tuple of empty strings.
    input: file_path, "cred=", file_path, "cred=", None, None
    output: ("", "")
    """
    testinput = ("usrn4.txt", "", "pw4.txt", obfuscate(""), None, None)
    assert ("", "") == execute_get_credentials_with_varying_input(*testinput)


def test_windows_authentication_from_input_should_return_empty_strings(execute_get_credentials_with_varying_input):
    """Windows authentication from user input - return tuple of empty strings.
    input: None, None, None, None, "", ""
    output: ("", "")
    """
    testinput = (None, None, None, None, "", "")
    assert ("", "") == execute_get_credentials_with_varying_input(*testinput)


def test_input_should_be_asked_when_file_missing(execute_get_credentials_with_varying_input):
    """File paths given but files do not exist - ask credentials from user.
    input: file_path, None, file_path, None, "USER5", "PASSWORD5"
    output: ("USER5", "PASSWORD5")
    """
    testinput = ("usrn5.txt", None, "pw5.txt", None, "USER5", "PASSWORD5")
    assert ("USER5", "PASSWORD5") == execute_get_credentials_with_varying_input(
        *testinput)


def test_password_should_not_be_asked_if_pw_prompt_is_none(execute_get_credentials_with_varying_input):
    """Parameter value pw_prompt=None -> do not ask for password -> password is empty string.
    input: file_path, "cred=USER", None, None, "USER3", "PASSWORD3"
    output: ("USER3", "")
    """
    testinput = ("usrn3.txt", "USER", None, None, "USER3", "PASSWORD3", False)
    assert ("USER3", "") == execute_get_credentials_with_varying_input(*testinput)
