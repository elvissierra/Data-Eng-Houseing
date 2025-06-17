import pandas as pd
import os
import glob

def find_latest_report(directory='.'):
    excluded_file = {"report_config.csv", "analytics_report.csv"}
    csv_file = glob.glob(os.path.join(directory, "*.csv"))
    csv_file = [f for f in csv_file if os.path.basename(f) not in excluded_file]
    if not csv_file:
        return None
    latest_file = max(csv_file, key=os.path.getmtime)
    return latest_file

def load_config_file(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    return pd.read_csv(config_path)

def generate_analytics_report(report_df, config_df, output_path="analytics_report.csv"):
    report_df.columns = report_df.columns.str.strip().str.lower()
    config_df.columns = config_df.columns.str.strip().str.lower()

    report_data = {}

    for col in config_df.columns:
        if col not in report_df.columns:
            print(f"⚠️ Warning: Column '{col}' not found in report. Skipping.")
            continue
        # Fetch and normalize headers
        target_value = str(config_df.iloc[0][col]).strip().lower()
        col_series = report_df[col].dropna().astype(str).str.lower().str.strip()
        # match count cases
        match_count = col_series.apply(lambda x: target_value in [i.strip() for i in x.split('|')]).sum()
        # blank count cases
        blank_count = report_df[col].isna().sum() + (report_df[col].astype(str).str.strip() == '').sum()
        # add calculations
        calc_percentage = (match_count / (len(report_df) - blank_count)) * 100 if len(report_df) - blank_count > 0 else 0

        report_data[col] = {
            "match_count": match_count,
            "blank_count": blank_count,
            "percentage": calc_percentage,
            #"": 
        }

    analytics_df = pd.DataFrame(report_data).T
    analytics_df = analytics_df.T
    analytics_df.to_csv(output_path)
    print(f"✅ Report generated: {output_path}")
    return analytics_df

if __name__ == "__main__":
    latest_report = find_latest_report()
    if not latest_report:
        raise FileNotFoundError("No report file found.")
    print(f"📄 Using latest report: {latest_report}")

    config_path = "report_config.csv"
    config_df = load_config_file(config_path)
    report_df = pd.read_csv(latest_report)

    df_result = generate_analytics_report(report_df, config_df)
    print(df_result)
