import pytest


@pytest.mark.tsql
def test_tsql_mark():
    assert 1 == 1

@pytest.mark.tsql
def test_tsql_mark2():
    assert 1 == 1

@pytest.mark.tsql
def test_tsql_mark3():
    assert 1 == 1
