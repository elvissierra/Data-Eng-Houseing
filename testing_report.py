import pandas as pd
import glob
import os


def find_latest_report(directory='.'):
    csv_file = glob.glob(os.path.join(directory, "*.csv"))
    if not csv_file:
        return None
    latest_file = max(csv_file, key=os.path.getmtime)
    return latest_file

def load_config_file(config_path):
    """ Loads the config file to analyze fields to generate. """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found, ready the config for report.")
    config_df = pd.read_csv(config_path)
    return config_df

def generate_analytics_report(report_df, config_df, output_path="analytics_report.csv"):
    selected_columns = config_df["column"].tolist()
    valid_columns = [col for col in selected_columns if col in report_df.columns]

    if not valid_columns:
        raise ValueError("Issue verifying headers in config.")

    selected_df = report_df[valid_columns]

    analytics = []

    for col in valid_columns:
        field1_count = 0
        field2_count = 0
        neither_count = 0
        for val in selected_df[col].dropna():
            fields = [x.strip().lower() for x in str(val).split('|')]
            has_field1 = 'field1' in fields
            has_field2 = 'field2' in fields
            if has_field1:
                field1_count += 1
            if has_field2:
                field2_count += 1
            if not has_field1 and not has_field2:
                neither_count += 1
        analytics.append({
            "column": col,
            "field1_count": field1_count,
            "field2_count": field2_count,
            "neither_count": neither_count
        })

    analytics_df = pd.DataFrame(analytics)
    analytics_df.to_csv(output_path, index=False)
    print(f"Report generated: {output_path}")
    return analytics_df

if __name__ == "__main__":
    latest_report = find_latest_report()
    if not latest_report:
        raise FileNotFoundError("No report file found in the current directory.")
    print(f"Latest report: {latest_report}")
    config_path = "report_config.csv"
    config_df = load_config_file(config_path)
    report_df = pd.read_csv(latest_report)

    df_result = generate_analytics_report(report_df, config_df)
    print(df_result)