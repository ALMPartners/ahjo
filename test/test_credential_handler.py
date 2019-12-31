"""
input: username file name, username file content, password file name, password file content, username input, password input
output: (username, password)
"""
from base64 import b64encode
from os import remove

import pytest

import ahjo.credential_handler as ahjo


def obfuscate(stng):
    return b64encode(stng.encode()).decode()


@pytest.fixture()
def execute_get_credentials_with_varying_input(tmp_path, monkeypatch):
    created_records = []

    def get_credentials(usrn_file_name, usrn_file_content, pw_file_name, pw_file_content, usrn_input, pw_input):
        # create username file if file naem and content given
        usrn_file_path = None
        if usrn_file_name and usrn_file_content is not None:
            usrn_file_path = tmp_path / usrn_file_name
            usrn_file_path.write_text(
                f"cred={usrn_file_content}", encoding="utf-8")
            created_records.append(str(usrn_file_path))
        # create password file if file naem and content given
        pw_file_path = None
        if pw_file_name and pw_file_content is not None:
            pw_file_path = tmp_path / pw_file_name
            pw_file_path.write_text(
                f"cred={pw_file_content}", encoding="utf-8")
            created_records.append(str(pw_file_path))
        # monkeypatch username and password input
        monkeypatch.setattr('builtins.input', lambda x: usrn_input)
        monkeypatch.setattr('getpass.getpass', lambda x: pw_input)
        return ahjo.get_credentials(usrn_file_path=usrn_file_path, pw_file_path=pw_file_path)

    yield get_credentials

    # suorittaa huolimatta get_credentials tuloksesta
    for record in created_records:
        remove(record)


def test_credentials_should_be_read_from_file_when_both_paths_given(execute_get_credentials_with_varying_input):
    """Molemmat filut annettu - lue filuista
    input: file_path, "cred=UKKELI", file_path, "cred=SALASANA", None, None
    output: ("UKKELI", "SALASANA")
    """
    testinput = ("usrn1.txt", "UKKELI1", "pw1.txt", obfuscate("SALASANA1"), None, None)
    assert ("UKKELI1", "SALASANA1") == execute_get_credentials_with_varying_input(*testinput)


def test_credentials_should_be_asked_when_username_file_not_given(execute_get_credentials_with_varying_input):
    """Username filua ei annettu - kysy input
    input: None, None, file_path, "cred=SALASANA", "UKKELI", "SALASANA"
    output: ("UKKELI", "SALASANA")
    """
    testinput = (None, None, "pw2.txt", obfuscate("SALASANA"), "UKKELI2", "SALASANA2")
    assert ("UKKELI2", "SALASANA2") == execute_get_credentials_with_varying_input(*testinput)


def test_credentials_should_be_asked_when_password_file_not_given(execute_get_credentials_with_varying_input):
    """Salasana filua ei annettu - kysy input
    input: file_path, "cred=UKKELI", None, None, "UKKELI", "SALASANA"
    output: ("UKKELI", "SALASANA")
    """
    testinput = ("usrn3.txt", "UKKELI", None, None, "UKKELI3", "SALASANA3")
    assert ("UKKELI3", "SALASANA3") == execute_get_credentials_with_varying_input(*testinput)


def test_credentials_should_be_asked_when_both_files_not_given(execute_get_credentials_with_varying_input):
    """Kumpaakaan filua ei annettu - kysy input
    input: None, None, None, None, "UKKELI", "SALASANA"
    output: ("UKKELI", "SALASANA")
    """
    testinput = (None, None, None, None, "UKKELI4", "SALASANA4")
    assert ("UKKELI4", "SALASANA4") == execute_get_credentials_with_varying_input(*testinput)


def test_windows_authentication_from_files_should_return_empty_strings(execute_get_credentials_with_varying_input):
    """WA filuista - palauttaa tyhjän merkkijonon
    input: file_path, "cred=", file_path, "cred=", None, None
    output: ("", "")
    """
    testinput = ("usrn4.txt", "", "pw4.txt", obfuscate(""), None, None)
    assert ("", "") == execute_get_credentials_with_varying_input(*testinput)


def test_windows_authentication_from_input_should_return_empty_strings(execute_get_credentials_with_varying_input):
    """WA inputista - palauttaa tyhjän merkkijonon
    input: None, None, None, None, "", ""
    output: ("", "")
    """
    testinput = (None, None, None, None, "", "")
    assert ("", "") == execute_get_credentials_with_varying_input(*testinput)


def test_input_should_be_asked_when_file_missing(execute_get_credentials_with_varying_input):
    """Filut annettu parametreina, mutta ei olemassa - kysy input
    input: file_path, None, file_path, None, "UKKELI", "SALASANA"
    output: ("UKKELI", "SALASANA")
    """
    testinput = ("usrn5.txt", None, "pw5.txt", None, "UKKELI5", "SALASANA5")
    assert ("UKKELI5", "SALASANA5") == execute_get_credentials_with_varying_input(*testinput)
