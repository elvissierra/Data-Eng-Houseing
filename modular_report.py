import pandas as pd
import csv
import os
import glob
import re


def find_latest_report(directory="ReportingAuto/"):
    excluded = {"report_config.csv", "Analytics_Report.csv"}
    files = glob.glob(os.path.join(directory, "*.csv"))
    files = [f for f in files if os.path.basename(f) not in excluded]
    return max(files, key=os.path.getmtime) if files else None


def load_config_file(config_path):
    """ Loads report_config, entries start at row 2 """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    return pd.read_csv(config_path, header=0)


def normalize_columns(df):
    """ Normalize columns. """
    df.columns = df.columns.str.strip().str.lower()
    return df


def write_custom_report(output_path, sections):
    """ Write to csv output. """
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        for section in sections:
            writer.writerows(section)
            writer.writerow([])


def generate_dynamic_report(report_df, config_df, output_path="ReportingAuto/Analytics_Report.csv"):
    """ Sectioned by column A in report_config """
    # normalize data
    report_df = normalize_columns(report_df)
    total_config = len(config_df)
    total_rows = len(report_df)
    # normalize config
    cfg = config_df.copy()
    cfg.columns = cfg.columns.str.strip().str.lower().str.replace(" ", "_")
    cfg["column"] = cfg["column"].astype(str).str.strip()
    
    # determine output calcs
    if "value" in cfg.columns:
        cfg["value"] = cfg["value"].fillna("").astype(str).str.lower()
    else:
        cfg["value"] = ""
    if "aggregate" in cfg.columns:
        cfg["aggregate"] = (cfg["aggregate"].fillna(False).astype(str).str.strip().str.lower().isin(["yes","true","1"]))
    else:
        cfg["aggregate"] = False
    if "root_only" in cfg.columns:
        cfg["root_only"] = (cfg["root_only"].fillna(False).astype(str).str.strip().str.lower().isin(["yes","true","1"]))
    else:
        cfg["root_only"] = False
    if "separate_nodes" in cfg.columns:
        cfg["separate_nodes"] = (cfg["separate_nodes"].fillna(False).astype(str).str.strip().str.lower().isin(["yes","true","1"]))
    else:
        cfg["separate_nodes"] = False
    if "delimiter" in cfg.columns:
        cfg["delimiter"] = cfg["delimiter"].fillna("|").astype(str)
    else:
        cfg["delimiter"] = ""

    # build sections
    sections = []
    sections.append([["Total rows", "", total_config]])

    for col_name in cfg["column"].unique():
        section = [[col_name.upper(), "%", "Count"]]
        entries = cfg[cfg["column"] == col_name]
        label_counts = {}
        # calculations for a specified value
        specific = entries[entries["value"] != ""]
        if not specific.empty:
            # only count specified values
            for _, r in specific.iterrows():
                orig = report_df[col_name].fillna("").astype(str)
                # separate nodes with pandas explode method
                if r["separate_nodes"]:
                    items = (orig.str.split(rf"\s*{re.escape(r["delimiter"])}\s*", regex=True).explode().dropna().str.strip().str.lower())
                    cnt = int((items == r["value"]).sum())
                else:
                    series = orig
                    if r["root_only"]:
                        series = series.str.split(re.escape(r["delimiter"]), expand=True)[0]
                    pattern = fr"(?:^|\|)\s*{re.escape(r["value"])}\s*(?:\||$)"
                    cnt = int(series.str.lower().str.contains(pattern).sum())
                label = r["value"] or "None"
                label_counts[label] = cnt
        else:
            # no entry in value == full field calcs
            for _, r in entries.iterrows():
                orig = report_df[col_name].fillna("").astype(str)
                
                if r["separate_nodes"]:
                    items = (orig.str.split(rf"\s*{re.escape(r["delimiter"])}\s*", regex=True).explode().dropna().str.strip().str.lower())
                    for val in items:
                        label = val or "None"
                        label_counts[label] = label_counts.get(label, 0) + 1

                elif r["aggregate"]:
                    series = orig
                    if r["root_only"]:
                        series = series.str.split(re.escape(r["delimiter"]), expand=True)[0]
                    for val in sorted(series.str.strip().str.lower().unique()):
                        label = val or "None"
                        cnt = int((series.str.strip().str.lower() == val).sum())
                        label_counts[label] = cnt
                
                else:
                    series = orig
                    if r["root_only"]:
                        series = series.str.split(re.escape(r["delimiter"]), expand=True)[0]
                    pattern = fr"(?:^|\|)\s*{re.escape(r["value"])}\s*(?:\||$)"
                    cnt = int(series.str.lower().str.contains(pattern).sum())
                    label = r["value"] or "None"
                    label_counts[label] = label_counts.get(label, 0) + cnt

        # append sections
        for label, cnt in label_counts.items():
            pct = round(cnt / total_rows * 100, 2)
            section.append([label, f"{pct:.2f}%", cnt])

        sections.append(section)

    write_custom_report(output_path, sections)
    print(f"✅ Report generated: {output_path}")

if __name__ == "__main__":
    latest = find_latest_report()
    if not latest:
        raise FileNotFoundError("No valid report_config found.")
    print(f"📄 Using report: {latest}")
    cfg = load_config_file("ReportingAuto/report_config.csv")
    df = pd.read_csv(latest)
    generate_dynamic_report(df, cfg)