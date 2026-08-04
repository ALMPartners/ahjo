# Ahjo - Database deployment framework
#
# Copyright 2019 - 2026 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

"""Module for comparing data from two dataframes and reporting differences."""

from logging import getLogger
from pathlib import Path

import time

try:
    import polars as pl
except:
    pl = None


logger = getLogger("ahjo")


def csv_to_pl_df(
    path: str | Path,
    *,
    separator: str = ",",
    columns: list[str] | None = None):
    """Read a CSV file into a Polars DataFrame.

    Parameters
    ----------
    path : str | Path
        Path to the CSV file.
    separator : str
        Column separator character.
    columns : list[str] | None
        If provided, only read these columns.

    Returns
    -------
    pl.DataFrame
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    df = pl.read_csv(path, separator=separator, columns=columns)
    logger.info(f"  Read {df.height} rows × {df.width} cols from {path.name}")
    return df


def filter_rows(a, b, filter_column: str, filter_value: str):
    """Filter both DataFrames to rows where ``filter_column`` equals ``filter_value``.

    The comparison is performed on string-cast values so type differences
    between the two sources (e.g. numeric vs text) do not affect filtering.

    Parameters
    ----------
    a : pl.DataFrame
        First source table.
    b : pl.DataFrame
        Second source table.
    filter_column : str
        Column used for filtering. Must be present in both sources.
    filter_value : str
        Value the filter column must equal.

    Returns
    -------
    tuple[pl.DataFrame, pl.DataFrame]
        Filtered copies of ``a`` and ``b``.

    Raises
    ------
    KeyError
        If ``filter_column`` is not present in either source.
    """
    if filter_column not in a.columns:
        raise KeyError(f"Filter column '{filter_column}' not found in source A.")
    if filter_column not in b.columns:
        raise KeyError(f"Filter column '{filter_column}' not found in source B.")

    a = a.filter(pl.col(filter_column).cast(pl.Utf8) == filter_value)
    b = b.filter(pl.col(filter_column).cast(pl.Utf8) == filter_value)
    return a, b


def compare_columns(
    a,
    b,
    key_cols: list[str] | None = None,
    compare_cols: list[str] | None = None):
    """Compare two DataFrames column-by-column after joining on keys.

    Parameters
    ----------
    a : pl.DataFrame
        First source table.
    b : pl.DataFrame
        Second source table.
    key_cols : list[str] | None
        Columns used as join keys. If None, comparison is done
        without joining (set-based row comparison).
    compare_cols : list[str] | None
        Columns to compare for differences. Only columns present in both
        sources are used. If None, all columns common to both sources
        (excluding key columns) are compared.

    Returns
    -------
    pl.DataFrame
        Rows with at least one difference. Contains original columns from
        both sources plus boolean ``<col>_diff`` flags.
    """
    start_time = time.time()

    common_cols = sorted(set(a.columns) & set(b.columns))

    if key_cols is None:
        key_cols = []

    # Determine value columns to compare
    if compare_cols is not None:
        value_cols = [c for c in compare_cols if c in common_cols and c not in key_cols]
        skipped = [c for c in compare_cols if c not in common_cols]
        if skipped:
            logger.warning(f"Columns not present in both sources (skipped): {skipped}")
    else:
        value_cols = [c for c in common_cols if c not in key_cols]

    if not value_cols:
        logger.warning("No columns to compare.")
        return pl.DataFrame()

    # Narrow both frames to relevant columns
    select_cols = key_cols + value_cols
    a_sel = a.select(select_cols)
    b_sel = b.select(select_cols)

    # Cast mismatched key columns to string on both sides so types match when
    # joining (e.g. a varchar key read as i64 from a CSV). Keys that already
    # share a type are left untouched.
    if key_cols:
        mismatched_keys = [c for c in key_cols if a_sel.schema[c] != b_sel.schema[c]]
        if mismatched_keys:
            a_sel = a_sel.with_columns([pl.col(c).cast(pl.Utf8) for c in mismatched_keys])
            b_sel = b_sel.with_columns([pl.col(c).cast(pl.Utf8) for c in mismatched_keys])

    # Join
    if key_cols:
        # joined contains all rows from both sources, 
        # with nulls for missing values
        joined = a_sel.join(
            b_sel,
            on=key_cols,
            how="full", # full outer join to detect missing rows in either source
            coalesce=True, # avoid suffixes for key columns
            suffix="_B",
        )
    else:
        # No keys – positional row-by-row comparison
        joined = _compare_positional(a_sel, b_sel)

    # Detect rows only in A or only in B based on null pattern in value columns
    b_cols = [f"{c}_B" for c in value_cols]
    all_a_null = pl.all_horizontal([pl.col(c).is_null() for c in value_cols])
    all_b_null = pl.all_horizontal([pl.col(c).is_null() for c in b_cols])
    joined = joined.with_columns(
        pl.when(all_b_null).then(pl.lit("A_only"))
          .when(all_a_null).then(pl.lit("B_only"))
          .otherwise(pl.lit("both"))
          .alias("_source")
    )

    # Build diff expressions per column (only for rows present in both)
    _NUMERIC_TYPES = (
        pl.Int8, pl.Int16, pl.Int32, pl.Int64,
        pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
        pl.Float32, pl.Float64,
        pl.Decimal,
    )
    diff_exprs = []
    for col in value_cols:
        col_b = f"{col}_B"
        col_a_expr = pl.col(col)
        col_b_expr = pl.col(col_b)
        type_a = joined.schema[col]
        type_b = joined.schema[col_b]
        if type_a != type_b:
            a_is_numeric = isinstance(type_a, _NUMERIC_TYPES)
            b_is_numeric = isinstance(type_b, _NUMERIC_TYPES)
            if a_is_numeric or b_is_numeric:
                # Cast both to Float64 so "1.0" == "1.00". Use non-strict cast so
                # non-numeric values (e.g. a "D" in a mostly-numeric varchar column)
                # become null instead of raising. Rows differ when their string
                # values differ, unless they are numerically equal.
                num_a = pl.col(col).cast(pl.Float64, strict=False)
                num_b = pl.col(col_b).cast(pl.Float64, strict=False)
                str_a = pl.col(col).cast(pl.Utf8)
                str_b = pl.col(col_b).cast(pl.Utf8)
                numerically_equal = num_a.is_not_null() & num_b.is_not_null() & num_a.eq(num_b)
                diff_exprs.append(
                    (
                        (str_a.ne(str_b) & ~numerically_equal)
                        | (str_a.is_null() & str_b.is_not_null())
                        | (str_a.is_not_null() & str_b.is_null())
                    ).alias(f"{col}_diff")
                )
                continue
            else:
                # Both non-numeric but different types: compare as strings
                col_a_expr = col_a_expr.cast(pl.Utf8)
                col_b_expr = col_b_expr.cast(pl.Utf8)
        diff_exprs.append(
            (
                col_a_expr.ne(col_b_expr)
                | (col_a_expr.is_null() & col_b_expr.is_not_null())
                | (col_a_expr.is_not_null() & col_b_expr.is_null())
            ).alias(f"{col}_diff")
        )

    result = joined.with_columns(diff_exprs)

    # Keep rows that are missing from one source OR have at least one column difference
    any_diff = pl.any_horizontal([pl.col(f"{c}_diff") for c in value_cols])
    is_missing = pl.col("_source") != "both"
    differing_rows = result.filter(any_diff | is_missing)

    elapsed = time.time() - start_time
    logger.info(f"  Comparison completed in {elapsed:.2f}s", extra={"info_type": "success"})

    return differing_rows


def _compare_positional(a, b):
    """Positional row-by-row comparison without join keys.

    Row 1 in A is compared to row 1 in B, etc. If one source has
    more rows, the extras are paired with nulls (reported as missing).

    Returns a joined DataFrame with columns from A, suffixed columns
    from B, and a ``_row`` column indicating the 1-based row number.
    """
    # Add a row index to both frames for positional alignment
    a_idx = a.with_row_index("_row").with_columns((pl.col("_row") + 1).cast(pl.Int64))
    b_idx = b.with_row_index("_row").with_columns((pl.col("_row") + 1).cast(pl.Int64))

    # Full join on the row index to handle unequal lengths
    joined = a_idx.join(
        b_idx,
        on="_row",
        how="full",
        coalesce=True,
        suffix="_B",
    )

    return joined


def print_diffs(
    results,
    key_cols: list[str] | None,
    value_cols: list[str],
    source_a: str = "A",
    source_b: str = "B") -> None:
    """Print differing rows to console.

    Parameters
    ----------
    results : pl.DataFrame
        DataFrame containing the comparison results.
    key_cols : list[str] | None
        List of key columns used for comparison.
    value_cols : list[str]
        List of value columns compared.
    source_a : str
        Label for the first source (e.g. file name or db object).
    source_b : str
        Label for the second source.
    """
    logger.info("\nResults", extra={"info_type": "header"})
    logger.info("-" * 50)

    if results.height == 0:
        logger.info("  No differences found\n")
        return

    # Count missing rows
    a_only = results.filter(results["_source"] == "A_only")
    b_only = results.filter(results["_source"] == "B_only")
    both = results.filter(results["_source"] == "both") if "_source" in results.columns else results

    if a_only.height > 0:
        logger.info(f"  Rows only in {source_a}: {a_only.height}")
    if b_only.height > 0:
        logger.info(f"  Rows only in {source_b}: {b_only.height}")
    if key_cols:
        logger.info(f"  Rows with differences: {both.height}")
        diff_cols = [f"{c}_diff" for c in value_cols if f"{c}_diff" in both.columns]
        if diff_cols:
            differing_cells = int(
                both.select(
                    pl.sum_horizontal([pl.col(c).cast(pl.Int64) for c in diff_cols]).sum()
                ).item()
            )
        else:
            differing_cells = 0
        logger.info(f"  Differing cells: {differing_cells}")
        
    logger.info("\n  Differences:\n")

    if key_cols:
        for row in both.iter_rows(named=True):
            changed = [c for c in value_cols if row.get(f"{c}_diff")]
            if changed:
                key_str = ", ".join(f"{k} = {row[k]}" for k in key_cols)
                logger.info(f"    Key: {key_str}")
                for col in changed:
                    val_a = row.get(col)
                    val_b = row.get(f"{col}_B")
                    logger.info(f"      {col}: {source_a} = {val_a} -> {source_b} = {val_b}")
                print()
    else:
        # Positional comparison output
        for row in both.iter_rows(named=True):
            changed = [c for c in value_cols if row.get(f"{c}_diff")]
            if changed:
                row_num = row.get("_row", "?")
                logger.info(f"    Row {row_num}:")
                for col in changed:
                    val_a = row.get(col)
                    val_b = row.get(f"{col}_B")
                    logger.info(f"      {col}: {source_a} = {val_a} -> {source_b} = {val_b}")
                print()


def format_results(
    results,
    key_cols: list[str] | None,
    value_cols: list[str],
    source_a: str = "A",
    source_b: str = "B"):
    """Reshape comparison results into a user-friendly table.

    Output column order:
        <key_cols> | _source | <source_a>_<col1> | <source_b>_<col1> | <col1>_comp | ...

    For each value column, ``<col>_comp`` is:
        - ``"OK"``        if the values are equal
        - ``"Different"`` if both rows exist but the values differ
        - ``"Missing"``   if the row is present in only one source

    The boolean ``<col>_diff`` columns are dropped.

    Parameters
    ----------
    results : pl.DataFrame
        DataFrame returned by :func:`compare_columns`.
    key_cols : list[str] | None
        Key columns used for the comparison. If ``None`` and a positional
        ``_row`` column is present, ``_row`` is used as the leftmost column.
    value_cols : list[str]
        Value columns that were compared.
    source_a : str
        Label used as the prefix for the first source's value columns.
    source_b : str
        Label used as the prefix for the second source's value columns.

    Returns
    -------
    pl.DataFrame
    """
    if results.height == 0:
        return results

    key_cols = key_cols or []
    leading = list(key_cols)
    if not leading and "_row" in results.columns:
        leading = ["_row"]

    # Build comparison expressions and renames
    rename_map = {}
    comp_exprs = []
    for col in value_cols:
        col_b = f"{col}_B"
        diff_col = f"{col}_diff"
        rename_map[col] = f"{source_a}_{col}"
        rename_map[col_b] = f"{source_b}_{col}"
        comp_exprs.append(
            pl.when(pl.col("_source") != "both").then(pl.lit("Missing"))
              .when(pl.col(diff_col)).then(pl.lit("Different"))
              .otherwise(pl.lit("OK"))
              .alias(f"{col}_comp")
        )

    formatted = results.with_columns(comp_exprs).rename(rename_map)

    # Final column order
    ordered = list(leading)
    if "_source" in formatted.columns:
        ordered.append("_source")
    for col in value_cols:
        ordered.extend([f"{source_a}_{col}", f"{source_b}_{col}", f"{col}_comp"])

    # Drop *_diff and any unexpected leftovers, keep only ordered columns that exist
    ordered = [c for c in ordered if c in formatted.columns]
    return formatted.select(ordered)