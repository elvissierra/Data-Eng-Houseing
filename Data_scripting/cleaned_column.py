import argparse
import os
import sys
import pandas as pd
import re

#to run -> python3 cleaned_column.py -i Untitled.csv -c this -o Untitled_output.csv

def clean_markings(s: str) -> str:
    """
    Remove square brackets and single/double quotes from the string,
    preserving commas, hyphens, spaces, and original casing.
    """
    if not isinstance(s, str):
        return s
    return re.sub(r"[\[\]\"']+", "", s)

def main():
    parser = argparse.ArgumentParser(
        description="Clean markings from one column in a CSV, preserving commas and casing."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to the input CSV file (e.g. csv_files/Untitled.csv)"
    )
    parser.add_argument(
        "-c", "--column",
        required=True,
        help="Name of the column to clean"
    )
    parser.add_argument(
        "-o", "--output_col",
        required=True,
        help="Path to write CSV of just the cleaned column"
    )
    parser.add_argument(
        "-f", "--full_output",
        help="(Optional) Path to write the full DataFrame with cleaned column; if omitted, input is overwritten"
    )
    args = parser.parse_args()

    # Validate input
    if not os.path.isfile(args.input):
        print(f"❌ Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Load
    df = pd.read_csv(args.input)
    if args.column not in df.columns:
        print(f"❌ Column '{args.column}' not in {args.input}", file=sys.stderr)
        sys.exit(1)

    # Clean
    df[args.column] = df[args.column].fillna("").astype(str).apply(clean_markings)

    # Write full DataFrame
    full_dest = args.full_output or args.input
    df.to_csv(full_dest, index=False)
    print(f"✅ Full DataFrame with cleaned '{args.column}' written to: {full_dest}")

    # Write column-only CSV
    df[[args.column]].to_csv(args.output_col, index=False)
    print(f"✅ Cleaned column '{args.column}' written to: {args.output_col}")

if __name__ == "__main__":
    main()