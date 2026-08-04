"""Tests for ahjo.operations.general.compare."""

import logging
import pytest
import ahjo.operations.general.compare as compare

pl = pytest.importorskip("polars", reason="polars is required for compare tests")


@pytest.fixture
def simple_frames():
    """Two frames sharing keys with one differing value and one matching."""
    a = pl.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["alice", "bob", "carol"],
            "amount": [100, 200, 300],
        }
    )
    b = pl.DataFrame(
        {
            "id": [1, 2, 3],
            "name": ["alice", "bob", "carol"],
            "amount": [100, 999, 300],  # row id=2 differs
        }
    )
    return a, b


# ---------------------------------------------------------------------------
# csv_to_pl_df
# ---------------------------------------------------------------------------

def test_csv_to_pl_df_reads_file(tmp_path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("id,name\n1,alice\n2,bob\n")

    df = compare.csv_to_pl_df(csv_path)

    assert df.height == 2
    assert df.columns == ["id", "name"]
    assert df["name"].to_list() == ["alice", "bob"]


def test_csv_to_pl_df_custom_separator(tmp_path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("id;name\n1;alice\n")

    df = compare.csv_to_pl_df(csv_path, separator=";")

    assert df.height == 1
    assert df["name"].to_list() == ["alice"]


def test_csv_to_pl_df_selected_columns(tmp_path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("id,name,extra\n1,alice,x\n")

    df = compare.csv_to_pl_df(csv_path, columns=["id", "name"])

    assert df.columns == ["id", "name"]


def test_csv_to_pl_df_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        compare.csv_to_pl_df(tmp_path / "does_not_exist.csv")


# ---------------------------------------------------------------------------
# compare_columns - key based
# ---------------------------------------------------------------------------

def test_compare_columns_detects_value_difference(simple_frames):
    a, b = simple_frames

    result = compare.compare_columns(a, b, key_cols=["id"])

    # Only the differing row (id=2) should be returned
    assert result.height == 1
    row = result.row(0, named=True)
    assert row["id"] == 2
    assert row["amount_diff"] is True
    assert row["name_diff"] is False
    assert row["_source"] == "both"


def test_compare_columns_no_differences_returns_empty(simple_frames):
    a, _ = simple_frames

    result = compare.compare_columns(a, a, key_cols=["id"])

    assert result.height == 0


def test_compare_columns_detects_missing_rows():
    a = pl.DataFrame({"id": [1, 2], "val": ["x", "y"]})
    b = pl.DataFrame({"id": [2, 3], "val": ["y", "z"]})

    result = compare.compare_columns(a, b, key_cols=["id"])

    sources = {row["id"]: row["_source"] for row in result.iter_rows(named=True)}
    assert sources[1] == "A_only"
    assert sources[3] == "B_only"
    assert 2 not in sources  # id=2 matches, so it is not reported


def test_compare_columns_only_compares_selected_columns():
    a = pl.DataFrame({"id": [1], "x": [1], "y": [1]})
    b = pl.DataFrame({"id": [1], "x": [1], "y": [99]})

    # Restrict comparison to column x; y differs but should be ignored
    result = compare.compare_columns(a, b, key_cols=["id"], compare_cols=["x"])

    assert result.height == 0


def test_compare_columns_skips_unknown_compare_cols(simple_frames, caplog):
    a, b = simple_frames

    compare.compare_columns(
        a, b, key_cols=["id"], compare_cols=["amount", "missing_col"]
    )

    assert "missing_col" in caplog.text


def test_compare_columns_no_value_cols_returns_empty(caplog):
    a = pl.DataFrame({"id": [1]})
    b = pl.DataFrame({"id": [1]})

    result = compare.compare_columns(a, b, key_cols=["id"])

    assert result.height == 0
    assert "No columns to compare" in caplog.text


# ---------------------------------------------------------------------------
# compare_columns - type coercion
# ---------------------------------------------------------------------------

def test_compare_columns_numeric_vs_string_no_false_diff():
    # Source A has float, source B has string representation with extra decimals
    a = pl.DataFrame({"id": [1], "amount": [40000000.0]})
    b = pl.DataFrame({"id": [1], "amount": ["40000000.00"]})

    result = compare.compare_columns(a, b, key_cols=["id"])

    # Values are numerically equal, so no difference should be reported
    assert result.height == 0


def test_compare_columns_int_vs_string_real_difference():
    a = pl.DataFrame({"id": [1], "amount": [100]})
    b = pl.DataFrame({"id": [1], "amount": ["200"]})

    result = compare.compare_columns(a, b, key_cols=["id"])

    assert result.height == 1
    assert result.row(0, named=True)["amount_diff"] is True


def test_compare_columns_numeric_column_with_nonnumeric_values_no_crash():
    # Source A is varchar with a non-numeric value ("D"), source B is numeric.
    # Mixed types must not raise during numeric coercion.
    a = pl.DataFrame({"id": [1, 2, 3], "vaade": ["21", "891", "D"]})
    b = pl.DataFrame({"id": [1, 2, 3], "vaade": [21, 891, 814]})

    result = compare.compare_columns(a, b, key_cols=["id"])

    # Only id=3 differs ("D" vs 814); numeric values 21/891 match
    assert result.height == 1
    assert result.row(0, named=True)["id"] == 3
    assert result.row(0, named=True)["vaade_diff"] is True


def test_compare_columns_mismatched_key_types_no_crash():
    # Key column is str on one side, int on the other (CSV inferred numeric).
    a = pl.DataFrame({"id": ["1010", "1800"], "val": ["x", "y"]})
    b = pl.DataFrame({"id": [1010, 1800], "val": ["x", "z"]})

    result = compare.compare_columns(a, b, key_cols=["id"])

    # Keys match after string coercion; only id=1800 value differs
    assert result.height == 1
    assert result.row(0, named=True)["id"] == "1800"


# ---------------------------------------------------------------------------
# compare_columns - positional (no keys)
# ---------------------------------------------------------------------------

def test_compare_columns_positional_difference():
    a = pl.DataFrame({"val": ["x", "y", "z"]})
    b = pl.DataFrame({"val": ["x", "DIFF", "z"]})

    result = compare.compare_columns(a, b)

    assert "_row" in result.columns
    assert result.height == 1
    assert result.row(0, named=True)["_row"] == 2


def test_compare_columns_positional_unequal_length():
    a = pl.DataFrame({"val": ["x", "y"]})
    b = pl.DataFrame({"val": ["x"]})

    result = compare.compare_columns(a, b)

    # Row 2 exists only in A
    assert result.height == 1
    row = result.row(0, named=True)
    assert row["_row"] == 2
    assert row["_source"] == "A_only"


# ---------------------------------------------------------------------------
# format_results
# ---------------------------------------------------------------------------

def test_format_results_column_layout(simple_frames):
    a, b = simple_frames
    results = compare.compare_columns(a, b, key_cols=["id"])

    formatted = compare.format_results(results, ["id"], ["name", "amount"])

    assert formatted.columns == [
        "id",
        "_source",
        "A_name",
        "B_name",
        "name_comp",
        "A_amount",
        "B_amount",
        "amount_comp",
    ]
    # No *_diff boolean columns should remain
    assert not any(c.endswith("_diff") for c in formatted.columns)


def test_format_results_comp_values(simple_frames):
    a, b = simple_frames
    results = compare.compare_columns(a, b, key_cols=["id"])

    formatted = compare.format_results(results, ["id"], ["name", "amount"])
    row = formatted.row(0, named=True)

    assert row["name_comp"] == "OK"
    assert row["amount_comp"] == "Different"


def test_format_results_missing_status():
    a = pl.DataFrame({"id": [1], "val": ["x"]})
    b = pl.DataFrame({"id": [2], "val": ["y"]})
    results = compare.compare_columns(a, b, key_cols=["id"])

    formatted = compare.format_results(results, ["id"], ["val"])

    statuses = set(formatted["val_comp"].to_list())
    assert statuses == {"Missing"}


def test_format_results_empty_input_returns_input():
    empty = pl.DataFrame()
    out = compare.format_results(empty, ["id"], ["val"])
    assert out.height == 0


def test_format_results_positional_uses_row_column():
    a = pl.DataFrame({"val": ["x", "y"]})
    b = pl.DataFrame({"val": ["x", "DIFF"]})
    results = compare.compare_columns(a, b)

    formatted = compare.format_results(results, None, ["val"])

    assert formatted.columns[0] == "_row"


def test_format_results_uses_source_labels(simple_frames):
    a, b = simple_frames
    results = compare.compare_columns(a, b, key_cols=["id"])

    formatted = compare.format_results(
        results, ["id"], ["name", "amount"], "left.csv", "right.csv"
    )

    assert "left.csv_name" in formatted.columns
    assert "right.csv_amount" in formatted.columns


# ---------------------------------------------------------------------------
# print_diffs
# ---------------------------------------------------------------------------

def test_print_diffs_no_differences(caplog):
    caplog.set_level(logging.INFO, logger="ahjo")
    empty = pl.DataFrame()
    compare.print_diffs(empty, ["id"], ["val"])
    assert "No differences found" in caplog.text


def test_print_diffs_reports_keys_and_values(simple_frames, caplog):
    caplog.set_level(logging.INFO, logger="ahjo")
    a, b = simple_frames
    results = compare.compare_columns(a, b, key_cols=["id"])

    compare.print_diffs(results, ["id"], ["name", "amount"])

    assert "id = 2" in caplog.text
    assert "amount" in caplog.text


def test_print_diffs_uses_source_labels(caplog):
    caplog.set_level(logging.INFO, logger="ahjo")
    a = pl.DataFrame({"id": [1, 2], "val": ["x", "y"]})
    b = pl.DataFrame({"id": [1, 3], "val": ["x", "z"]})
    results = compare.compare_columns(a, b, key_cols=["id"])

    compare.print_diffs(results, ["id"], ["val"], "left.csv", "RECON.dbo.t")

    assert "Rows only in left.csv" in caplog.text
    assert "Rows only in RECON.dbo.t" in caplog.text


# ---------------------------------------------------------------------------
# filter_rows
# ---------------------------------------------------------------------------

def test_filter_rows_filters_both_sources():
    a = pl.DataFrame({"datadate": [20190228, 20190301], "val": ["x", "y"]})
    b = pl.DataFrame({"datadate": [20190228, 20190228], "val": ["x", "z"]})

    fa, fb = compare.filter_rows(a, b, "datadate", "20190228")

    assert fa.height == 1
    assert fb.height == 2
    assert fa["val"].to_list() == ["x"]


def test_filter_rows_string_cast_matches_numeric():
    # filter_value is a string but the column is numeric
    a = pl.DataFrame({"k": [1, 2], "val": ["a", "b"]})
    b = pl.DataFrame({"k": [1, 2], "val": ["a", "b"]})

    fa, fb = compare.filter_rows(a, b, "k", "1")

    assert fa.height == 1
    assert fb.height == 1


def test_filter_rows_missing_column_in_a_raises():
    a = pl.DataFrame({"val": ["x"]})
    b = pl.DataFrame({"datadate": [20190228], "val": ["x"]})

    with pytest.raises(KeyError):
        compare.filter_rows(a, b, "datadate", "20190228")


def test_filter_rows_missing_column_in_b_raises():
    a = pl.DataFrame({"datadate": [20190228], "val": ["x"]})
    b = pl.DataFrame({"val": ["x"]})

    with pytest.raises(KeyError):
        compare.filter_rows(a, b, "datadate", "20190228")

