from ahjo.operations.general.scan import is_hetu, valid_search_rules, DEFAULT_SCAN_RULES

VALID_HETUS = [
    "010105A991P","140892-944N","140892-9296","151188-983Y",
    "151188-910L","010150+9854","021123A922U","150454-991T","180898+902E",
    "150801A995F","100715A9033","130785-981L","140865-971K","130854-9702"
]

INVALID_HETUS = [
    "", "notValid", "123456-7890", "123456-789", "1234567890", "123456789",
    "311299A934B", "000588-943W", "121388-943W", "320891-966S"
]

VALID_FILEPATHS = [
    ("database/data/file.sql", ["^database/"]),
    ("database/data/file.sql", ["^database/data/"]),
    ("database/data/file.sql", ["database/data/file.sql"]),
    ("database/data/employee.sql" , ["database/data/employee.sql$"]),
    ("database/procedures/test.sql", [r"^database/(data|procedures)/.*\.sql"]),
    ("database/data/dm.DimTest.sql", [r"^database/data/dm\..*"]),
    ("test.sql", ["^.*"]),
    ("database/data/test.sql", ["^.*"])
]

INVALID_FILEPATHS = [
    ("database/data/file.sql", ["^database/procedures"]),
    ("alembic/test.py", ["^database/"]),
    ("", "^.*"),
    ("database/data/file.sqlx" , ["database/data/file.sql$"]),
    ("database/test/test.sql", [r"^database/(data|procedures)/.*\.sql"]),
    ("database/data/dmx.DimTest.sql", [r"^database/data/dm\..*"]),
]

def test_is_hetu_should_return_true_for_valid_hetu():
    for hetu in VALID_HETUS:
        assert is_hetu(hetu) is True

def test_is_hetu_should_return_false_for_invalid_hetu():
    for hetu in INVALID_HETUS:
        assert is_hetu(hetu) is False

def test_valid_search_rules_should_return_true_for_valid_search_rules():
    assert valid_search_rules(DEFAULT_SCAN_RULES) is True

def test_valid_search_rules_should_raise_error_if_input_not_list():
    try:
        valid_search_rules("not a list")
    except Exception as err:
        assert type(err) == TypeError

def test_valid_search_rules_should_return_false_for_empty_search_rules():
    assert valid_search_rules([]) is False

def test_valid_search_rules_should_return_false_for_none_search_rules():
    assert valid_search_rules(None) is False

def test_valid_search_rules_should_return_false_for_invalid_type():
    assert	valid_search_rules(123) is False
