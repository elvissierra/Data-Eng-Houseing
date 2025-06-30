import pandas as pd
import csv
import os
import glob
import re

# Modular Report Generator for reporting on CSV files

def find_latest_report(directory="csv_files/"):
    """ Finds most recent CSV report file in current directory. """
    excluded_file = {"ICFI.csv", "report_config.csv", "testing_report_config.csv", "Analytics_Report.csv", "testing_report_config.csv", "Report_Ticket.csv"}
    csv_files = glob.glob(os.path.join(directory, "*.csv"))
    csv_files = [f for f in csv_files if os.path.basename(f) not in excluded_file]
    return max(csv_files, key=os.path.getmtime) if csv_files else None

def load_config_file(config_path):
    """ Loads report_config """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    return pd.read_csv(config_path)

def normalize_columns(df):
    """ Normalize headers """
    df.columns = df.columns.str.strip().str.lower()
    return df

def write_custom_report(output_path, section_data):
    """ Write report to CSV """
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        for section in section_data:
            writer.writerows(section)
            writer.writerow([])

def generate_dynamic_report(report_df, config_df, output_path="Analytics_Report.csv"):
    """ Generate Configurable Report """
    #determine total rows
    total_rows = len(report_df)
    #init data blocks
    section_blocks = []
    #normalize headers
    report_df = normalize_columns(report_df)
    #copy config_df to avoid modifying original
    config_df = config_df.copy()
    #normalize config headers
    config_df.columns = config_df.columns.str.strip().str.lower()
    #ensure required columns exist

    config_df["value"] = (config_df["value"].fillna("").astype(str).str.lower())
    config_df["aggregate"] = (config_df["aggregate"].fillna("").astype(str).str.strip().str.lower().isin(["yes", "true", "1"]))
    config_df["root_only"] = (config_df).get("root_only", "").str.strip().str.lower().isin(["yes", "true", "1"])
    config_df["delimiter"] = (config_df).get("delimiter", " ")
    #enable enum for the specified rows
    #config_df["seperate_nodes"] = (config_df["seperate_nodes"].fillna("").astype(str).str.strip().str.lower().isin(["yes", "true", "1"]))
    config_df["label"] = (config_df).get("label", "")
    #get unique groups
    groups = config_df["group"].unique()

    for group in groups:
        group_df = config_df[config_df["group"] == group]
        section = [[f"{group}", "%", "Count"]]

        for _, row in group_df.iterrows():
            col = row["column"].strip().lower()
            target_value = str(row.get("value", "")).strip().lower()
            is_aggregate = row["aggregate"]
            is_root = row["root_only"]
            delimiter = row["delimiter"] or r"/|"
            #seperate_nodes = row["seperate_nodes"]
            label = target_value or row.get("label")

            if col not in report_df.columns:
                print(f"⚠️ Warning: '{col}' not found in report. Skipping.")
                continue
            series = report_df[col].fillna("").astype(str)

            if target_value:
                for val in series:
                    if isinstance(val, str):
                        val = val.strip().lower()
                        return val
            if is_root:
                series = series.str.split(re.escape(delimiter)).str[0]

            if is_aggregate:
                unique_values = series.str.strip().str.lower().unique()
                for val in sorted(unique_values):
                    match = series.str.strip().str.lower().eq(val)
                    match_count = int(match.sum())
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

            #if seperate_nodes:
            #    expand = (series.str.split(r"\s*\|\s*", regex=True).explode().str.strip().str.lower())
            #    counts = expand.value_counts()
            #    for val, count in counts.items():
            #        percent = round((count / total_rows) * 100, 2)
            #        section.append([val, f"{percent:.2f}%", count])

        section_blocks.append(section)

    write_custom_report(output_path, section_blocks)
    print(f"✅ Report generated: {output_path}")


if __name__ == "__main__":
    latest_report = find_latest_report()
    if not latest_report:
        raise FileNotFoundError("No valid report CSV found.")
    print(f"📄 Using latest report: {latest_report}")

    config_path = "csv_files/report_config.csv"
    config_df = load_config_file(config_path)
    report_df = pd.read_csv(latest_report)

    generate_dynamic_report(report_df, config_df)
