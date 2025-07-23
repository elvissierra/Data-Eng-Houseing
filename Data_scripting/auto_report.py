import pandas as pd
import csv
import os
import glob
import re
import ast


def clean_list_string(s, sep=", "):
    if not isinstance(s, str):
        return s
    s = s.strip()
    try:
        items = ast.literal_eval(s)
        if isinstance(items, (list, tuple)):
            items = [str(i).strip() for i in items if str(i).strip()]
            return sep.join(items)
    except (ValueError, SyntaxError):
        pass

    return re.sub(r"[\[\]'\"]+", "", s)

def find_latest_report(directory="csv_files/"):
    """ find latest csv outside of config and output report """
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
    """ Normalize columns """
    df.columns = df.columns.str.strip().str.lower()
    return df


def write_custom_report(output_path, sections):
    """ Write to csv output """
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        for section in sections:
            writer.writerows(section)
            writer.writerow([])


def generate_dynamic_report(report_df, config_df, output_path="csv_files/Analytics_Report.csv"):
    """ Sectioned by column A in report_config """
# normalize data
    report_df = normalize_columns(report_df)
    total_config = len(config_df)
    total_rows = len(report_df)
    # normalize config
    cfg = config_df.copy()
    cfg.columns = cfg.columns.str.strip().str.lower().str.replace(" ", "_")
    cfg["column"] = cfg["column"].astype(str).str.strip()

    # clean column headers
    if "value" in cfg.columns:
        cfg["value"] = cfg["value"].fillna("").astype(str).str.lower()
    else:
        cfg["value"] = ""

    if "aggregate" in cfg.columns:
        cfg["aggregate"] = (
            cfg["aggregate"].fillna(False).astype(str).str.strip().str.lower().isin(["yes", "true"]))
    else:
        cfg["aggregate"] = False

    if "root_only" in cfg.columns:
        cfg["root_only"] = (cfg["root_only"].fillna(False).astype(str).str.strip().str.lower().isin(["yes", "true"]))
    else:
        cfg["root_only"] = False

    if "separate_nodes" in cfg.columns:
        cfg["separate_nodes"] = (cfg["separate_nodes"].fillna(False).astype(str).str.strip().str.lower().isin(["yes", "true"]))
    else:
        cfg["separate_nodes"] = False

    if "delimiter" in cfg.columns:
        cfg["delimiter"] = cfg["delimiter"].fillna("|").astype(str)
    else:
        cfg["delimiter"] = ""

    if "average" in cfg.columns:
        cfg["average"] = (cfg["average"].fillna(False).astype(str).str.strip().str.lower().isin(["yes", "true"]))
    else:
        cfg["average"] = False

    if "duplicate" in cfg.columns:
       cfg["duplicate"] = (cfg["duplicate"].fillna(False).astype(str).str.strip().str.lower().isin(["yes", "true"]))
    else:
        cfg["duplicate"] = False
      # handle clean option: if selected, clean column values using clean_list_string
    if "clean" in cfg.columns:
        cfg["clean"] = (
            cfg["clean"]
               .fillna(False)
               .astype(str)
               .str.strip()
               .str.lower()
               .isin(["yes", "true"])
        )
    else:
        cfg["clean"] = False
  
    # apply cleaning to report_df for columns marked 'clean'
    for clean_col in cfg.loc[cfg["clean"], "column"]:
        report_df[clean_col] = (
            report_df[clean_col]
            .fillna("")
            .astype(str)
            .apply(clean_list_string)
        )

    # build sections
    sections = []
    sections.append([["Total rows", "", total_config]])

    for col_name in cfg["column"].unique():
        
        # locate duplicates and instances
        if cfg.loc[cfg["column"] == col_name, "duplicate"].any():
            raw = report_df[col_name].fillna("").astype(str)
            counts = raw.value_counts()
            duplicate =  counts[counts > 1]
            section = [[col_name.upper(), "", "Duplicate"]]
            for value, cnt in duplicate.items():
                section.append([value, "", cnt])
            sections.append(section)
            continue

        # calc average of column, provided integers
        if cfg.loc[cfg["column"] == col_name, "average"].any():
            raw = report_df[col_name].fillna("").astype(str)
            if not raw.str.match(r"^\d+(\.\d+)?%?$").all():
                # if non digit
                sections.append(
                    [[col_name.upper(), "", "Average"], ["Non-digit field", "", ""]]
                )
            else:
                nums = pd.to_numeric(raw.str.rstrip("%"), errors="coerce")
                avg = nums.mean()
                unit = "%" if raw.str.endswith("%").any() else ""
                sections.append(
                    [[col_name.upper(), "", "Average"], ["", "", f"{avg:.2f}{unit}"]]
                )
            continue

        entries = cfg[cfg["column"] == col_name]
        label_counts = {}
        # populate label counts
        search_value = entries[entries["value"] != ""]

        if not search_value.empty:
            # search VALUE entry
            for _, r in search_value.iterrows():
                series = report_df[col_name].fillna("").astype(str)
                # separate nodes with pandas explode method
                if r["separate_nodes"]:
                    items = (
                        series.str.split(
                            rf"\s*{re.escape(r["delimiter"])}\s*", regex=True
                        )
                        .explode()
                        .dropna()
                        .str.strip()
                        .str.lower()
                        .apply(clean_list_string)
                    )
                    cnt = int((items == r["value"]).sum())
                else:
                    if r["root_only"]:
                        series = series.str.split(
                            re.escape(r["delimiter"]), expand=True
                        )[0]
                    pattern = rf"(?:^|\|)\s*{re.escape(r["value"])}\s*(?:\||$)"
                    cnt = int(series.str.lower().str.contains(pattern).sum())
                label = r["value"] or "None"
                label_counts[label] = cnt
        else:
            # no specified VALUE entry
            for _, r in entries.iterrows():
                series = report_df[col_name].fillna("").astype(str)
                # explode indexes by provided delimiter
                if r["separate_nodes"]:
                    items = (
                        series.str.split(
                            rf"\s*{re.escape(r["delimiter"])}\s*", regex=True
                        ).explode().dropna().str.strip().str.lower())
                    for val in items:
                        label = val or "None"
                        label_counts[label] = label_counts.get(label, 0) + 1
                # aggregate column
                elif r["aggregate"]:
                    # return index[0] provided delimiter
                    if r["root_only"]:
                        series = series.str.split(re.escape(r["delimiter"]), expand=True)[0]
                    for val in sorted(series.str.strip().str.lower().unique()):
                        label = val or "None"
                        cnt = int((series.str.strip().str.lower() == val).sum())
                        label_counts[label] = cnt
                else:
                # index[0] provided a str
                    if r["root_only"]:
                        series = series.str.split(
                            re.escape(r["delimiter"]), expand=True
                        )[0]
                    pattern = rf"(?:^|\|)\s*{re.escape(r["value"])}\s*(?:\||$)"
                    cnt = int(series.str.lower().str.contains(pattern).sum())
                    label = r["value"] or "None"
                    label_counts[label] = label_counts.get(label, 0) + cnt

        section = [[col_name.upper(), "%", "Count"]]
        for label, cnt in label_counts.items():
            pct = round(cnt / total_rows * 100, 2)
            section.append([label, f"{pct:.2f}%", cnt])
        sections.append(section)

    write_custom_report(output_path, sections)
    print(f"✅ Report generated: {output_path}")


if __name__ == "__main__":
    # report directory fix
    current_dir = os.getcwd()
    dir_name = os.path.basename(current_dir)
    #if dir_name == 'csv_files':
    #    report_dir = ''
    #elif dir_name == 'atx-movate-places':
    report_dir = 'csv_files/'
    #else:
    #    raise FileNotFoundError(f"Unrecognized directory '{dir_name}'. No valid report_config found.")
    latest = find_latest_report(report_dir)
    if not latest:
        raise FileNotFoundError("No valid report_config found.")
    print(f"📄 Using report: {latest}")
    cfg = load_config_file(f"{report_dir}report_config.csv")
    df = pd.read_csv(latest)
    generate_dynamic_report(df, cfg, output_path=f"{report_dir}Analytics_Report.csv")