import pandas as pd
import csv
import os
import glob
import re

# -- Helper functions ---------------------------------------------------------

def find_latest_report(directory="csv_files/"):
    excluded = {
        "ICFI.csv", "report_config.csv", "testing_report_config.csv",
        "Analytics_Report.csv", "Report_Ticket.csv"
    }
    files = glob.glob(os.path.join(directory, "*.csv"))
    files = [f for f in files if os.path.basename(f) not in excluded]
    return max(files, key=os.path.getmtime) if files else None


def load_config_file(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    return pd.read_csv(config_path, header=0)


def normalize_columns(df):
    df.columns = df.columns.str.strip().str.lower()
    return df


def write_custom_report(output_path, sections):
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        for section in sections:
            writer.writerows(section)
            writer.writerow([])

# -- Core Report Generator --------------------------------------------------

def generate_dynamic_report(
    report_df,
    config_df,
    output_path="Analytics_Report.csv",
    wide_format=False,
    include_group=False
):
    """
    Generate a configurable report.

    Long format (default): sections by column name, optionally grouped by 'group'.
    Wide format: pivot with MultiIndex columns (column, label), optionally adding group.
    """
    # Normalize data
    report_df = normalize_columns(report_df)
    total_rows = len(report_df)

    # Normalize config
    cfg = config_df.copy()
    cfg.columns = cfg.columns.str.strip().str.lower()
    cfg['group']  = cfg.get('group', '').astype(str).str.strip().str.lower()
    cfg['column'] = cfg['column'].astype(str).str.strip()

    # Prepare flags
    num_cfg = len(cfg)
    cfg['value']          = cfg['value'].fillna('').astype(str).str.lower() if 'value' in cfg else ['']*num_cfg
    cfg['aggregate']      = (cfg['aggregate'].fillna(False).astype(str).str.strip().str.lower().isin(['yes','true','1']) if 'aggregate' in cfg else [False]*num_cfg)
    cfg['root_only']      = (cfg['root_only'].fillna(False).astype(str).str.strip().str.lower().isin(['yes','true','1']) if 'root_only' in cfg else [False]*num_cfg)
    cfg['separate_nodes'] = (cfg['separate_nodes'].fillna(False).astype(str).str.strip().str.lower().isin(['yes','true','1']) if 'separate_nodes' in cfg else [False]*num_cfg)
    cfg['delimiter']      = cfg['delimiter'].fillna('|').astype(str) if 'delimiter' in cfg else ['|']*num_cfg

    # Build flat rows for pivot or long sections
    rows = []
    for _, r in cfg.iterrows():
        col_key = r['column'].lower()
        if col_key not in report_df.columns:
            continue
        series = report_df[col_key].fillna('').astype(str)
        if r['root_only']:
            series = series.str.split(re.escape(r['delimiter']), expand=True)[0]

        # Extract items
        if r['separate_nodes']:
            items = (series
                     .str.split(rf"\s*{re.escape(r['delimiter'])}\s*", regex=True)
                     .explode().dropna()
                     .str.strip().str.lower())
            counts = items.value_counts()
            for val, cnt in counts.items():
                rows.append({
                    'group': r['group'],
                    'column': r['column'],
                    'label': val,
                    'count': cnt,
                    'percent': round(cnt/total_rows*100,2)
                })
        elif r['aggregate']:
            for val in sorted(series.str.strip().str.lower().unique()):
                cnt = int((series.str.strip().str.lower()==val).sum())
                rows.append({
                    'group': r['group'],
                    'column': r['column'],
                    'label': val,
                    'count': cnt,
                    'percent': round(cnt/total_rows*100,2)
                })
        else:
            tgt = r['value']
            if r['root_only']:
                tgt = tgt.split(r['delimiter'])[0]
            pattern = fr"(?:^|\|)\s*{re.escape(tgt)}\s*(?:\||$)"
            cnt = int(series.str.lower().str.contains(pattern).sum())
            rows.append({
                'group': r['group'],
                'column': r['column'],
                'label': tgt,
                'count': cnt,
                'percent': round(cnt/total_rows*100,2)
            })

    df_long = pd.DataFrame(rows)

    if wide_format:
        # Wide: MultiIndex columns
        if include_group and 'group' in df_long:
            tuples = [
                (g, c, l)
                for g in cfg['group'].unique()
                for c in cfg[cfg['group']==g]['column'].unique()
                for l in df_long[(df_long['group']==g)&(df_long['column']==c)]['label'].unique()
            ]
            mi = pd.MultiIndex.from_tuples(tuples, names=['group','column','label'])
            data = {
                (g,c,l): df_long[(df_long['group']==g)&(df_long['column']==c)&(df_long['label']==l)]['count'].sum()
                for (g,c,l) in tuples
            }
        else:
            tuples = [
                (c, l)
                for c in cfg['column'].unique()
                for l in df_long[df_long['column']==c]['label'].unique()
            ]
            mi = pd.MultiIndex.from_tuples(tuples, names=['column','label'])
            data = {
                (c,l): df_long[(df_long['column']==c)&(df_long['label']==l)]['count'].sum()
                for (c,l) in tuples
            }
        wide_df = pd.DataFrame([data], columns=mi)
        wide_df.to_csv(output_path, index=False)
        print(f"✅ Wide report generated: {output_path}")
    else:
        # Long: sections by column, optional grouping
        sections = []
        sections.append([["Total rows","",total_rows]])
        if include_group and 'group' in df_long:
            for g in cfg['group'].unique():
                # group header
                sections.append([[g.upper(),"%","Count"]])
                for c in cfg[cfg['group']==g]['column']:
                    sections.append([[c.upper(),"%","Count"]])
                    subset = df_long[(df_long['group']==g)&(df_long['column']==c)]
                    for _, r in subset.iterrows():
                        sections.append([[r['label'],f"{r['percent']:.2f}%",r['count']]])
                    sections.append([[]])
        else:
            for c in cfg['column'].unique():
                sections.append([[c.upper(),"%","Count"]])
                subset = df_long[df_long['column']==c]
                for _, r in subset.iterrows():
                    sections.append([[r['label'],f"{r['percent']:.2f}%",r['count']]])
                sections.append([[]])
        write_custom_report(output_path, sections)
        print(f"✅ Long report generated: {output_path}")

if __name__ == '__main__':
    latest = find_latest_report()
    if not latest:
        raise FileNotFoundError('No valid report CSV found.')
    print(f"📄 Using report: {latest}")
    cfg = load_config_file('csv_files/report_config.csv')
    df = pd.read_csv(latest)
    generate_dynamic_report(df, cfg, wide_format=False, include_group=True)
