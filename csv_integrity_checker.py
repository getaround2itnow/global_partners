#!/usr/bin/env python3

"""
CSV Data Integrity Checker

Checks three CSV files for:
1. Duplicate rows
2. Missing values (count and percentage)
3. Corrupt / invalid values based on expected data rules
4. Basic referential-integrity problems between related files

Creates an Excel workbook named:
    csv_data_integrity_report.xlsx

Expected input files:
    date_dim.csv
    order_items.csv
    order_item_options.csv

Put this script in the same directory as the three CSV files and run:
    python csv_integrity_checker.py
"""

from pathlib import Path
import re

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CSV_DIR = Path(
    "/Users/marvinZ/DocumentsMacBookAir/Toshiba/Calendar/DE_Academy/"
    "Projects/End_to_End/Global_Partners/project_csv_files"
)

FILES = {
    "date_dim": CSV_DIR / "date_dim.csv",
    "order_items": CSV_DIR / "order_items.csv",
    "order_item_options": CSV_DIR / "order_item_options.csv",
}

OUTPUT_FILE = Path(__file__).resolve().parent / "csv_data_integrity_report.xlsx"

# Expected columns from the files shown in the screenshot.
EXPECTED_COLUMNS = {
    "date_dim": [
        "date_key",
        "year",
        "month",
        "week",
        "day_of_week",
        "is_weekend",
        "is_holiday",
        "holiday_name",
    ],
    "order_items": [
        "APP_NAME",
        "RESTAURANT_ID",
        "CREATION_TIME_UTC",
        "ORDER_ID",
        "USER_ID",
        "PRINTED_CARD_NUMBER",
        "IS_LOYALTY",
        "CURRENCY",
        "LINEITEM_ID",
        "ITEM_CATEGORY",
        "ITEM_NAME",
        "ITEM_PRICE",
        "ITEM_QUANTITY",
    ],
    "order_item_options": [
        "ORDER_ID",
        "LINEITEM_ID",
        "OPTION_GROUP_NAME",
        "OPTION_NAME",
        "OPTION_PRICE",
        "OPTION_QUANTITY",
    ],
}

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def is_missing(value):
    """Treat NaN, None, and blank/whitespace strings as missing."""
    if pd.isna(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False

def load_csv(path):
    """Read a CSV while preserving values as strings initially."""
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        na_values=["NULL", "null", "NA", "N/A", "NaN", "nan"],
    )

def add_issue(issues, file_name, row_number, column, value, issue_type, details):
    issues.append(
        {
            "file": file_name,
            "row": row_number,
            "column": column,
            "value": value,
            "issue_type": issue_type,
            "details": details,
        }   
    )

# ---------------------------------------------------------------------------
# Missing-value checks
# ---------------------------------------------------------------------------

def check_missing_values(df, file_name):
    results = []

    for column in df.columns:
        missing_count = df[column].apply(is_missing).sum()
        total = len(df)
        pct = (missing_count / total * 100) if total else 0

        results.append(
            {
                "file": file_name,
                "column": column,
                "total_rows": total,
                "missing_count": int(missing_count),
                "missing_percent": round(pct, 2),
            }
        )

    return results
# ---------------------------------------------------------------------------
# Duplicate checks
# ---------------------------------------------------------------------------

def check_duplicates(df, file_name):
    results = []

    duplicate_mask = df.duplicated(keep=False)
    duplicate_df = df.loc[duplicate_mask].copy()

    if duplicate_df.empty:
        return results

    # Add a human-readable original row number.
    duplicate_df["_source_row"] = duplicate_df.index + 2

    # Group identical rows so the report is easier to read.
    data_columns = list(df.columns)

    for _, group in duplicate_df.groupby(data_columns, dropna=False, sort=False):
        rows = group["_source_row"].tolist()

        results.append(
            {
                "file": file_name,
                "duplicate_group_size": len(rows),
                "source_rows": ", ".join(map(str, rows)),
                "duplicate_values": " | ".join(
                    f"{col}={group.iloc[0][col]}"
                    for col in data_columns
                ),
            }
        )

    return results
# ---------------------------------------------------------------------------
# Corrupt-value checks
# ---------------------------------------------------------------------------

def check_date_dim(df, issues):
    file_name = "date_dim.csv"

   
    # DD-MM-YYYY or MM-DD-YYYY format.

    for idx, value in df["date_key"].items():
        if is_missing(value):
            continue

    value_str = str(value).strip()

    valid_date = False

    for date_format in ["%d-%m-%Y", "%m-%d-%Y"]:
        try:
            pd.to_datetime(
                value_str,
                format=date_format
            )
            valid_date = True
            break
        except (ValueError, TypeError):
            pass

    if not valid_date:
        add_issue(
            issues, file_name, idx + 2, "date_key", value,
            "Invalid date",
            "Could not be parsed as DD-MM-YYYY or MM-DD-YYYY."
        )

    # Numeric/date-part checks.
    for column, min_value, max_value in [
        ("year", 2000, 2100),
        ("month", 1, 12),
        ("week", 1, 53),
    ]:
        numeric = pd.to_numeric(df[column], errors="coerce")

        for idx, value in df[column].items():
            if is_missing(value):
                continue

            number = numeric.loc[idx]

            if pd.isna(number):
                add_issue(
                    issues, file_name, idx + 2, column, value,
                    "Invalid numeric value",
                    f"{column} should be numeric."
                )
            elif not float(number).is_integer():
                add_issue(
                    issues, file_name, idx + 2, column, value,
                    "Invalid integer value",
                    f"{column} should contain whole numbers."
                )
            elif not (min_value <= number <= max_value):
                add_issue(
                    issues, file_name, idx + 2, column, value,
                    "Out-of-range value",
                    f"Expected {column} to be between {min_value} and {max_value}."
                )

    # Expected weekday names.
    valid_days = {
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"
    }

    for idx, value in df["day_of_week"].items():
        if not is_missing(value) and value not in valid_days:
            add_issue(
                issues, file_name, idx + 2, "day_of_week", value,
                "Invalid categorical value",
                "Expected a weekday name such as Monday or Sunday."
            )

    # Boolean checks.
    for column in ["is_weekend", "is_holiday"]:
        for idx, value in df[column].items():
            if not is_missing(value) and str(value).upper() not in {"TRUE", "FALSE"}:
                add_issue(
                    issues, file_name, idx + 2, column, value,
                    "Invalid boolean value",
                    "Expected TRUE or FALSE."
                )


def check_order_items(df, issues):
    file_name = "order_items.csv"

    # Boolean.
    for idx, value in df["IS_LOYALTY"].items():
        if not is_missing(value) and str(value).upper() not in {"TRUE", "FALSE"}:
            add_issue(
                issues, file_name, idx + 2, "IS_LOYALTY", value,
                "Invalid boolean value",
                "Expected TRUE or FALSE."
            )

    # Currency: typical ISO-4217 representation such as USD.
    currency_pattern = re.compile(r"^[A-Z]{3}$")

    for idx, value in df["CURRENCY"].items():
        if not is_missing(value) and not currency_pattern.fullmatch(str(value).strip()):
            add_issue(
                issues, file_name, idx + 2, "CURRENCY", value,
                "Invalid currency code",
                "Expected a 3-letter uppercase currency code such as USD."
            )

    # Price should be numeric and non-negative.
    prices = pd.to_numeric(df["ITEM_PRICE"], errors="coerce")

    for idx, value in df["ITEM_PRICE"].items():
        if is_missing(value):
            continue

        number = prices.loc[idx]

        if pd.isna(number):
            add_issue(
                issues, file_name, idx + 2, "ITEM_PRICE", value,
                "Invalid numeric value",
                "ITEM_PRICE should be numeric."
            )
        elif number < 0:
            add_issue(
                issues, file_name, idx + 2, "ITEM_PRICE", value,
                "Negative price",
                "ITEM_PRICE should normally be zero or greater."
            )

    # Quantity should be a positive whole number.
    quantities = pd.to_numeric(df["ITEM_QUANTITY"], errors="coerce")

    for idx, value in df["ITEM_QUANTITY"].items():
        if is_missing(value):
            continue

        number = quantities.loc[idx]

        if pd.isna(number):
            add_issue(
                issues, file_name, idx + 2, "ITEM_QUANTITY", value,
                "Invalid numeric value",
                "ITEM_QUANTITY should be numeric."
            )
        elif not float(number).is_integer() or number <= 0:
            add_issue(
                issues, file_name, idx + 2, "ITEM_QUANTITY", value,
                "Invalid quantity",
                "ITEM_QUANTITY should be a positive whole number."
            )

    # Timestamp should be parseable.
    timestamps = pd.to_datetime(df["CREATION_TIME_UTC"], errors="coerce", utc=True)

    for idx, value in df["CREATION_TIME_UTC"].items():
        if not is_missing(value) and pd.isna(timestamps.loc[idx]):
            add_issue(
                issues, file_name, idx + 2, "CREATION_TIME_UTC", value,
                "Invalid timestamp",
                "Could not be parsed as a valid UTC timestamp."
            )

def check_order_item_options(df, issues):
    file_name = "order_item_options.csv"

    # OPTION_PRICE should be numeric and non-negative.
    prices = pd.to_numeric(df["OPTION_PRICE"], errors="coerce")

    for idx, value in df["OPTION_PRICE"].items():
        if is_missing(value):
            continue

        number = prices.loc[idx]

        if pd.isna(number):
            add_issue(
                issues, file_name, idx + 2, "OPTION_PRICE", value,
                "Invalid numeric value",
                "OPTION_PRICE should be numeric."
            )
        elif number < 0:
            add_issue(
                issues, file_name, idx + 2, "OPTION_PRICE", value,
                "Negative option price",
                "OPTION_PRICE should normally be zero or greater."
            )

    # OPTION_QUANTITY should be a positive whole number.
    quantities = pd.to_numeric(df["OPTION_QUANTITY"], errors="coerce")

    for idx, value in df["OPTION_QUANTITY"].items():
        if is_missing(value):
            continue

        number = quantities.loc[idx]

        if pd.isna(number):
            add_issue(
                issues, file_name, idx + 2, "OPTION_QUANTITY", value,
                "Invalid numeric value",
                "OPTION_QUANTITY should be numeric."
            )
        elif not float(number).is_integer() or number <= 0:
            add_issue(
                issues, file_name, idx + 2, "OPTION_QUANTITY", value,
                "Invalid quantity",
                "OPTION_QUANTITY should be a positive whole number."
            )
# ---------------------------------------------------------------------------
# Schema checks
# ---------------------------------------------------------------------------

def check_columns(df, file_name, expected_columns, issues):
    actual = list(df.columns)

    missing_columns = [c for c in expected_columns if c not in actual]
    unexpected_columns = [c for c in actual if c not in expected_columns]

    if missing_columns:
        add_issue(
            issues, file_name, "N/A", "COLUMN STRUCTURE", "",
            "Missing column(s)",
            ", ".join(missing_columns)
        )

    if unexpected_columns:
        add_issue(
            issues, file_name, "N/A", "COLUMN STRUCTURE", "",
            "Unexpected column(s)",
            ", ".join(unexpected_columns)
        )
# ---------------------------------------------------------------------------
# Referential integrity checks
# ---------------------------------------------------------------------------

def check_referential_integrity(dataframes, issues):
    order_items = dataframes["order_items"]
    options = dataframes["order_item_options"]

    # Every option should point to an order/line item
    # that exists in order_items.
    parent_keys = set(
        zip(
            order_items["ORDER_ID"].astype(str),
            order_items["LINEITEM_ID"].astype(str),
        )
    )

    broken_rows = []

    for idx, row in options.iterrows():
        key = (
            str(row["ORDER_ID"]),
            str(row["LINEITEM_ID"])
        )

        if key not in parent_keys:
            add_issue(
                issues,
                "order_item_options.csv",
                idx + 2,
                "ORDER_ID / LINEITEM_ID",
                f"{row['ORDER_ID']} / {row['LINEITEM_ID']}",
                "Broken reference",
                "ORDER_ID + LINEITEM_ID does not exist in order_items.csv."
            )

            broken_rows.append(
                {
                    "source_row": idx + 2,
                    "ORDER_ID": row["ORDER_ID"],
                    "LINEITEM_ID": row["LINEITEM_ID"],
                    "OPTION_GROUP_NAME": row["OPTION_GROUP_NAME"],
                    "OPTION_NAME": row["OPTION_NAME"],
                    "OPTION_PRICE": row["OPTION_PRICE"],
                    "OPTION_QUANTITY": row["OPTION_QUANTITY"],
                }
            )

    return pd.DataFrame(broken_rows)
# ---------------------------------------------------------------------------
# Workbook creation
# ---------------------------------------------------------------------------

def autofit_worksheet(writer, sheet_name, dataframe):
    worksheet = writer.sheets[sheet_name]

    for column_cells in worksheet.columns:
        max_length = 0
        column_letter = column_cells[0].column_letter

        for cell in column_cells:
            value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, len(value))

        worksheet.column_dimensions[column_letter].width = min(max_length + 2, 60)

def investigate_missing_item_fields(dataframes):
    """
    Display order_items rows where LINEITEM_ID,
    ITEM_CATEGORY, or ITEM_NAME is missing.
    """

    order_items = dataframes["order_items"]

# is_missing catches NaN + blanks & spaces
    problem_rows = order_items[
        order_items["LINEITEM_ID"].apply(is_missing)
        | order_items["ITEM_CATEGORY"].apply(is_missing)
        | order_items["ITEM_NAME"].apply(is_missing)
    ]

    print("\nInvestigation: rows with missing item fields")
    print(f"Problem rows found: {len(problem_rows)}")

    if problem_rows.empty:
        print("No problem rows found.")
        return pd.DataFrame()

    print(problem_rows.to_string(index=False))

    # Use the ORDER_ID from the first problematic row.
    order_id = problem_rows.iloc[0]["ORDER_ID"]

    investigated_order = order_items[
        order_items["ORDER_ID"] == order_id
    ]

    print("\nAll rows belonging to this ORDER_ID:")
    print(investigated_order.to_string(index=False))

    print(
        f"\nNumber of rows in this order: "
        f"{len(investigated_order)}"
    )

    # Investigate zero-quantity rows.
    zero_quantity = order_items[
        order_items["ITEM_QUANTITY"].astype(str).str.strip() == "0"
    ]

    print(
        f"\nRows with ITEM_QUANTITY = 0: "
        f"{len(zero_quantity):,}"
    )

    print("\nITEM_QUANTITY data type:")
    print(order_items["ITEM_QUANTITY"].dtype)

    print("\nITEM_QUANTITY value for suspicious row:")
    print(repr(problem_rows.iloc[0]["ITEM_QUANTITY"]))

    print("\nUnique ITEM_QUANTITY values around zero:")
    print(
        order_items["ITEM_QUANTITY"]
        .astype(str)
        .str.strip()
        .value_counts()
        .loc[lambda x: x.index.isin(["0", "0.0"])]
    )

    return investigated_order

def investigate_option_duplicates(dataframes):
    """
    Investigate duplicate records in order_item_options.

    source_row:
        The smallest/original CSV row number in the duplicate group.

    duplicate_source_rows:
        All CSV row numbers belonging to the duplicate group.

    duplicate_count:
        Number of records in the duplicate group.

    exact_match:
        TRUE when OPTION_PRICE and OPTION_QUANTITY
        are identical across the duplicate group.
    """

    options = dataframes["order_item_options"].copy()

    # Preserve the original CSV row number.
    # +2 accounts for the header row and zero-based pandas index.
    options["source_row"] = options.index + 2

    # These columns define what constitutes a duplicate group.
    duplicate_columns = [
        "ORDER_ID",
        "LINEITEM_ID",
        "OPTION_GROUP_NAME",
        "OPTION_NAME"
    ]

    # Find how many times each duplicate group occurs.
    counts = (
        options
        .groupby(duplicate_columns)
        .size()
        .reset_index(name="duplicate_count")
    )

    duplicate_groups = counts[
        counts["duplicate_count"] > 1
    ]

    # Return every row belonging to a duplicate group.
    investigation = (
        options
        .merge(
            duplicate_groups,
            on=duplicate_columns,
            how="inner"
        )
    )

    # ---------------------------------------------------------
    # Determine whether the rows within each duplicate group
    # are identical in all remaining data columns.
    # ---------------------------------------------------------

    comparison_columns = [
        "OPTION_PRICE",
        "OPTION_QUANTITY"
    ]

    variation = (
        investigation
        .groupby(duplicate_columns)[comparison_columns]
        .nunique()
        .reset_index()
    )

    variation["exact_match"] = (
        (variation["OPTION_PRICE"] == 1)
        & (variation["OPTION_QUANTITY"] == 1)
    )

    investigation = investigation.merge(
        variation[
            duplicate_columns + ["exact_match"]
        ],
        on=duplicate_columns,
        how="left"
    )

    # ---------------------------------------------------------
    # Create a list of every source row belonging to each
    # duplicate group.
    # ---------------------------------------------------------

    source_rows = (
        investigation
        .groupby(duplicate_columns)["source_row"]
        .apply(
            lambda rows: ", ".join(
                str(row)
                for row in sorted(rows)
            )
        )
        .reset_index(
            name="duplicate_source_rows"
        )
    )

    investigation = investigation.merge(
        source_rows,
        on=duplicate_columns,
        how="left"
    )

    # ---------------------------------------------------------
    # source_row represents the smallest/original CSV row
    # number in each duplicate group.
    # ---------------------------------------------------------

    original_source_rows = (
        investigation
        .groupby(duplicate_columns)["source_row"]
        .min()
        .reset_index(
            name="original_source_row"
        )
    )

    investigation = investigation.merge(
        original_source_rows,
        on=duplicate_columns,
        how="left"
    )

    # Keep the original row number for every actual record,
    # but also provide the first row in the duplicate group.
    investigation = investigation.sort_values(
        duplicate_columns + ["source_row"]
    )

    # Put the most useful investigation columns first.
    investigation = investigation[
        [
            "source_row",
            "original_source_row",
            "duplicate_source_rows",
            "ORDER_ID",
            "LINEITEM_ID",
            "OPTION_GROUP_NAME",
            "OPTION_NAME",
            "OPTION_PRICE",
            "OPTION_QUANTITY",
            "duplicate_count",
            "exact_match"
        ]
    ]

    return investigation

def main():
    print("Starting CSV data-integrity check...\n")

    dataframes = {}
    all_missing = []
    all_duplicates = []
    all_issues = []

    # Load files.
    for name, path in FILES.items():
        if not path.exists():
            raise FileNotFoundError(
                f"Could not find {path.name} in {CSV_DIR}"
            )

        print(f"Reading {path.name}...")
        df = load_csv(path)
        dataframes[name] = df

        check_columns(
            df,
            path.name,
            EXPECTED_COLUMNS[name],
            all_issues
        )

        all_missing.extend(
            check_missing_values(df, path.name)
        )

        all_duplicates.extend(
            check_duplicates(df, path.name)
        )

        print(f"  Rows: {len(df):,}")
        print(f"  Columns: {len(df.columns)}")

    print("\nKeys currently stored in dataframes:")
    print(dataframes.keys())

    # Value-level validation.
    check_date_dim(dataframes["date_dim"], all_issues)
    check_order_items(dataframes["order_items"], all_issues)
    check_order_item_options(dataframes["order_item_options"], all_issues)

    # Cross-file validation.
    broken_references = check_referential_integrity(
        dataframes,
        all_issues
    )

    # Investigate broken references.
    order_items = dataframes["order_items"]

    if not broken_references.empty:

        # Show each unique broken ORDER_ID.
        # We only need ORDER_ID here because the investigation
        # will look for all line items belonging to that order.
        broken_keys = (
            broken_references[
                ["ORDER_ID"]
            ]
            .drop_duplicates()
        )

        # Count how many times each broken
        # ORDER_ID / LINEITEM_ID combination occurs.
        broken_reference_summary = (
            broken_references
            .groupby(
                ["ORDER_ID", "LINEITEM_ID"],
                as_index=False
            )
            .size()
            .rename(
                columns={"size": "occurrence_count"}
            )
            .sort_values(
                "occurrence_count",
                ascending=False
            )
        )

        # Find ALL order_items belonging to the affected orders.
        # This merge uses ORDER_ID only.
        order_item_investigation = (
            broken_keys.merge(
                order_items[
                    [
                        "ORDER_ID",
                        "LINEITEM_ID",
                        "RESTAURANT_ID",
                        "CREATION_TIME_UTC",
                        "USER_ID",
                        "ITEM_CATEGORY",
                        "ITEM_NAME",
                        "ITEM_PRICE",
                        "ITEM_QUANTITY"
                    ]
                ],
                on="ORDER_ID",
                how="left"
            )
            .sort_values(
                ["ORDER_ID", "LINEITEM_ID"]
            )
        )
        # Broken reference options;
        # Show the actual option records associated with
        # the broken references.
        option_investigation = (
            broken_references
            .sort_values(
                ["ORDER_ID", "LINEITEM_ID"]
            )
        )
        #Temporary adding to check values
        print("\nBroken references:")
        print(broken_references.shape)
        print(broken_references.columns.tolist())

        print("\nOrder item investigation:")
        print(order_item_investigation.shape)

        print("\nOption investigation:")
        print(option_investigation.shape)

           # Temporary diagnostic check:
        # Do the affected ORDER_IDs exist anywhere in order_items?
        affected_order_ids = (
            broken_references["ORDER_ID"]
            .drop_duplicates()
        )

        matching_orders = order_items[
            order_items["ORDER_ID"].isin(affected_order_ids)
        ]

        print("\nAffected ORDER_IDs:")
        print(affected_order_ids.to_list())

        print("\nMatching rows found in order_items:")
        print(matching_orders.to_string(index=False))

        print(
            f"\nNumber of matching order_items rows: "
            f"{len(matching_orders)}"
        )
        print(
        f"\nNumber of affected ORDER_IDs: "
        f"{len(affected_order_ids)}"
    )

    else:

        # No broken references were found.
        broken_keys = pd.DataFrame(
            columns=["ORDER_ID"]
        )

        broken_reference_summary = pd.DataFrame(
            columns=[
                "ORDER_ID",
                "LINEITEM_ID",
                "occurrence_count"
            ]
    )

    # Investigation.
    investigated_order = investigate_missing_item_fields(
        dataframes
    )

    duplicate_option_investigation = (
    investigate_option_duplicates(dataframes)
    )	

    # Summary.
    summary = []

    for name, df in dataframes.items():
        file_name = FILES[name].name
        missing_for_file = [
            x for x in all_missing if x["file"] == file_name
        ]
        duplicate_for_file = [
            x for x in all_duplicates if x["file"] == file_name
        ]
        issues_for_file = [
            x for x in all_issues if x["file"] == file_name
        ]

        total_missing = sum(
            x["missing_count"] for x in missing_for_file
        )

        summary.append(
            {
                "file": file_name,
                "rows": len(df),
                "columns": len(df.columns),
                "missing_values": total_missing,
                "duplicate_groups": len(duplicate_for_file),
                "corrupt_or_invalid_values": len(issues_for_file),
            }
        )

    summary_df = pd.DataFrame(summary)
    missing_df = pd.DataFrame(all_missing)
    duplicates_df = pd.DataFrame(all_duplicates)
    issues_df = pd.DataFrame(all_issues)

    if missing_df.empty:
        missing_df = pd.DataFrame(
            columns=[
                "file", "column", "total_rows",
                "missing_count", "missing_percent"
            ]
        )

    if duplicates_df.empty:
        duplicates_df = pd.DataFrame(
            columns=[
                "file", "duplicate_group_size",
                "source_rows", "duplicate_values"
            ]
        )

    if issues_df.empty:
        issues_df = pd.DataFrame(
            columns=[
                "file", "row", "column", "value",
                "issue_type", "details"
            ]
        )

   # Write Excel report.
    with pd.ExcelWriter(
        OUTPUT_FILE,
        engine="openpyxl"
    ) as writer:

        summary_df.to_excel(
            writer, sheet_name="Summary", index=False
        )

        missing_df.to_excel(
             writer, sheet_name="Missing Values", index=False
        )

        duplicates_df.to_excel(
             writer, sheet_name="Duplicates", index=False
       )

        issues_df.to_excel(
             writer, sheet_name="Corrupt Values", index=False
        )

       # A sheet showing the expected schemas is useful when debugging.
        schema_rows = []

        for name, columns in EXPECTED_COLUMNS.items():
            for position, column in enumerate(columns, start=1):
                schema_rows.append(
                    {
                        "file": FILES[name].name,
                        "column_position": position,
                        "expected_column": column,
                    }
                )

        pd.DataFrame(schema_rows).to_excel(
            writer, sheet_name="Expected Schema", index=False
        )
        investigated_order.to_excel(
            writer,
            sheet_name="Investigated Order",
            index=False
        )
        broken_references.to_excel(
            writer,
            sheet_name="Broken References",
            index=False
        )
        broken_reference_summary.to_excel(
            writer,
            sheet_name="Broken References Summary",
            index=False
        )
        order_item_investigation.to_excel(
            writer,
            sheet_name="Broken Reference Investigation",
            index=False
        )
        option_investigation.to_excel(
           writer,
           sheet_name="Broken Reference Options",
           index=False
        )
        duplicate_option_investigation.to_excel(
       writer,
        sheet_name="Duplicate Investigation",
        index=False
        )
    if not broken_references.empty:
            broken_reference_summary = (
                broken_references
                .groupby(
                    ["ORDER_ID", "LINEITEM_ID"],
                    as_index=False
                )
                .size()
                .rename(
                    columns={"size": "occurrence_count"})
                .sort_values(
                    "occurrence_count",
                    ascending=False
                )
            )
    else:
        broken_reference_summary = pd.DataFrame(
            columns=[
                "ORDER_ID",
                "LINEITEM_ID",
                "occurrence_count"
            ]
        )

       # Basic formatting.
        for sheet_name, df in {
            "Summary": summary_df,
            "Missing Values": missing_df,
            "Duplicates": duplicates_df,
            "Corrupt Values": issues_df,
            "Expected Schema": pd.DataFrame(schema_rows),
	        "Investigated Order": investigated_order,	
        }.items():
            autofit_worksheet(writer, sheet_name, df)

        print("\nIntegrity check complete!")
        print(f"Excel report created: {OUTPUT_FILE}")
        print("\nSummary:")

        for row in summary:
            print(

                f"{row['rows']:,} rows, "
                f"{row['missing_values']:,} missing values, "
                f"{row['duplicate_groups']:,} duplicate groups, "
                f"{row['corrupt_or_invalid_values']:,} invalid/corrupt values"
        )

if __name__ == "__main__":
    main()
