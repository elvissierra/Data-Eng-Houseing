#!/usr/bin/env python3
import argparse
import json
from typing import Dict, List, Callable
import glob
import sys
import os
import pandas as pd


def normalize_headers(df: pd.DataFrame):
    """Make headers safe for programmatic access."""
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"[^\w]+", "_", regex=True)
        .str.strip("_")
    )
    return df


def latest_csv(directory="."):
    """Returns the latest report csv file in the current directory."""
    csv_file = glob.glob(os.path.join(directory), "*.csv")
    if not csv_file:
        return None
    latest_file = max(csv_file, key=os.path.getctime)
    return latest_file


def load_report(latest_file, normalize: bool = True, **kwargs):
    """Read CSV into DataFrame, optionally normalizing headers."""
    df = pd.read_csv(latest_file, **kwargs)
    return normalize_headers(df) if normalize else df


def select_and_rename(
    df: pd.DataFrame, want: List[str], rename_map: Dict[str, str] = None
):
    """Keep only `want` columns (if they exist), and rename per `rename_map`."""
    present = [col for col in want if col in df.columns]
    out = df[present].copy()
    if rename_map:
        out = out.rename(columns=rename_map)
    return out


def apply_calculations(df: pd.DataFrame, calcs: Dict[str, str]):
    """
    Given a dict of new_col_name -> pandas-eval-able expression in terms of df,
    e.g. { "full_name": "first_name + ' ' + last_name", "age_days": "age * 365" }
    """
    df = df.copy()
    for new_col, expr in calcs.items():
        df[new_col] = df.eval(expr)
    return df


def save_csv(df: pd.DataFrame, path: str, **kwargs):
    df.to_csv(path, index=False, **kwargs)


def main():
    parser = argparse.ArgumentParser(
        description="Generic CSV → filtered, calculated report.csv"
    )
    parser.add_argument("input_csv", help="Path to source CSV")
    parser.add_argument("output_csv", help="Where to write your report")
    parser.add_argument(
        "--keep-cols",
        nargs="+",
        default=[],
        help="List of normalized column names to retain",
    )
    parser.add_argument(
        "--rename-map",
        type=json.loads,
        default={},
        help=(
            "JSON map raw_name:desired_name, e.g. "
            '\'{"ticket_id":"Ticket ID","url":"POI URL"}\''
        ),
    )
    parser.add_argument(
        "--calcs",
        type=json.loads,
        default={},
        help=(
            "JSON map new_col:pandas_expr, e.g. "
            '\'{"missing_hours":"operating_hours.isna()"}\''
        ),
    )
    args = parser.parse_args()

    # 1) load + normalize
    df = load_report(args.input_csv)

    # 2) pick & rename
    df = select_and_rename(df, args.keep_cols, args.rename_map)

    # 3) custom calcs
    if args.calcs:
        df = apply_calculations(df, args.calcs)

    # 4) write out
    save_csv(df, args.output_csv)
    print(f"Report written to {args.output_csv}")


if __name__ == "__main__":
    main()
