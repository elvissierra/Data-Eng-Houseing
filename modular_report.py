import pandas as pd
import csv
import os
import glob
import re

""" Report Aggregate- in the following long format

    GROUP        ,   COLUMN     ,     VALUE    , AGGREGATE, ROOT_ONLY, DELIMITER , LABEL
    Group name   , Col Header   ,  Row Value   ,   yes/no ,   yes/no ,    .      ,
EX. Cat Root Node,ModernCat-Name,              ,   yes    ,   yes    ,    .      , Does Nothing?
    Cat Head Node,ModernCat-Path,beauty_and_spa,   no     ,   yes    ,    .      ,
    Country Code , Country Code ,    us        ,          ,          ,           ,
    
"""

def find_latest_report(directory='.'):
    excluded_file = {"modular_report_config.csv", "analytics_report.csv", "testing_report_config.csv", "Report_Ticket.csv"}
    csv_files = glob.glob(os.path.join(directory, "*.csv"))
    csv_files = [f for f in csv_files if os.path.basename(f) not in excluded_file]
    return max(csv_files, key=os.path.getmtime) if csv_files else None

def load_config_file(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    return pd.read_csv(config_path)

def normalize_columns(df):
    df.columns = df.columns.str.strip().str.lower()
    return df

def write_custom_report(output_path, section_data):
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        for section in section_data:
            writer.writerows(section)
            writer.writerow([])

def generate_dynamic_report(report_df, config_df, output_path="analytics_report.csv"):
    total_rows = len(report_df)
    section_blocks = []

    report_df = normalize_columns(report_df)
    config_df = config_df.copy()
    config_df.columns = config_df.columns.str.strip().str.lower()
    config_df["aggregate"] = (config_df).get("aggregate", "").str.strip().str.lower().isin(['yes', 'true', '1'])
    config_df["root_only"] = (config_df).get("root_only", "").str.strip().str.lower().isin(['yes', 'true', '1'])
    config_df["delimiter"] = (config_df).get("delimiter", ".")

    groups = config_df['group'].unique()

    for group in groups:
        group_df = config_df[config_df['group'] == group]
        section = [[f"{group}", "%", "Count"]]  # header row

        for _, row in group_df.iterrows():
            col = row['column'].strip().lower()
            is_aggregate = row["aggregate"]
            target_value = str(row.get("value", "")).strip().lower()
            label = target_value or row.get('label')
            is_root = row["root_only"]
            delimiter = row["delimiter"]


            if col not in report_df.columns:
                print(f"⚠️ Warning: '{col}' not found in report. Skipping.")
                continue
            series = report_df[col].fillna("").astype(str)
            if is_root:
                series = series.str.split(re.escape(delimiter)).str[0]
            if is_aggregate:
                unique_values = series.str.strip().str.lower().unique()
                for val in sorted(unique_values):
                    mask = series.str.strip().str.lower().eq(val)
                    match_count = int(mask.sum())
                    percent = round((match_count / total_rows) * 100, 2)
                    section.append([val, f"{percent:.2f}%", match_count])
            else:
                if is_root:
                    target_value = target_value.split(delimiter)[0]
                pattern = fr"(?:^|\|)\s*{re.escape(target_value)}\s*(?:\||$)"
                matched = (
                    series.str.lower().str.contains(pattern)
                )
                match_count = int(matched.sum())
                percent = round(match_count / total_rows * 100, 2)
                section.append([label, f"{percent:.2f}%", match_count])

        section_blocks.append(section)

    write_custom_report(output_path, section_blocks)
    print(f"✅ Report generated: {output_path}")


if __name__ == "__main__":
    latest_report = find_latest_report()
    if not latest_report:
        raise FileNotFoundError("No valid report CSV found.")
    print(f"📄 Using latest report: {latest_report}")

    config_path = "modular_report_config.csv"
    config_df = load_config_file(config_path)
    report_df = pd.read_csv(latest_report)

    generate_dynamic_report(report_df, config_df)
