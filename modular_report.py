import pandas as pd
import csv
import os
import glob

def find_latest_report(directory='.'):
    excluded_file = {"report_config.csv", "analytics_report.csv"}
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

    groups = config_df['group'].unique()

    for group in groups:
        group_df = config_df[config_df['group'] == group]
        section = [[f"{group}", "%", "Count"]]  # header row
        
        for _, row in group_df.iterrows():
            col = row['column'].strip().lower()
            target_value = str(row['value']).strip().lower()
            label = row['label'] if 'label' in row and pd.notna(row['label']) else target_value

            if col not in report_df.columns:
                print(f"⚠️ Warning: '{col}' not found in report. Skipping.")
                continue

            matched = report_df[col].dropna().astype(str).str.lower().str.strip().apply(
                lambda x: target_value in [i.strip() for i in x.split('|')]
            )

            match_count = matched.sum()
            percent = round((match_count / total_rows) * 100, 2)

            section.append([label, f"{percent:.2f}%", match_count])

        section_blocks.append(section)

    write_custom_report(output_path, section_blocks)
    print(f"✅ Report generated: {output_path}")


if __name__ == "__main__":
    latest_report = find_latest_report()
    if not latest_report:
        raise FileNotFoundError("No valid report CSV found.")
    print(f"📄 Using latest report: {latest_report}")

    config_path = "report_config.csv"
    config_df = load_config_file(config_path)
    report_df = pd.read_csv(latest_report)

    generate_dynamic_report(report_df, config_df)
