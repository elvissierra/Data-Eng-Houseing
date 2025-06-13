import glob
import os
import pandas as pd
import csv

"""
    OPERATIONS = {
        # column_name:      row_name
        "Ticket Type": ("sum", "Ticket Type"), # ticket type [e.g. "New", "Update", "Delete"]
        "Last Editor Resolution": ("Complete", "Rejected"), # num of complete/ rejected
        "L1 Resolution": ("sum", "L1 Resolution"), # num of approved/ rejected
        "L2 Resolution": ("sum", "L1 Resolution"), # num of approved/ rejected
        "Suggested Fields": ("sum", "Suggested Fields"), # num per suggested field seen
        "Edited Fields": (), # per suggested field seen how many of each were edited
        "Other procedural markings?": (), # per suggested field seen how many of each have an 'other markings made along with procedural marking?'
        "All  customer suggested fields?": ("", ""), # how many are Yes, No, or NA
        "All customer suggested fields have a corresponding dependent edit?": ("", ""), # how many are Yes, No, or NA
        "Are customer issues resolved?": ("", ""), # how many are Yes, No, or NA
        "Any attribute errors remain on POI?": ("", ""), # how many are Yes, No, or NA
        "Are there still discrepancies between research indicators and POI data?": ("", ""), # how many are Yes, No, or NA
        "Correlation: P-W": ("", ""), # Correlation between Columns P and W
        "Correlation: S-W": ("", ""), # Correlation between Columns S and W
        "Correlation: T-X": ("", ""), # Correlation between Columns T and X
        #"": ("", ""),
    }
"""

INPUT_CSV = "ICFI.csv"
REPORTING_CSV = "Report_Ticket.csv"

TICKET_TYPES = [
    "POI Datascience", "POI Change Details",
    "POI Remove",      "POI Add",
]

possible_fields = ["Closures", "Name", "URL", "Address", "Geocode", "Phone", "All-Year-Round Hours", "Modern Category", "Category"]

LE_RES = ["Complete", "Reject"]
L1_RES = ["Approved", "Rejected"]
L2_RES = ["Approved", "Rejected"]

ALL_CUS1 = ["YES", "NO", "N/A"]
ALL_CUS2 = ["YES", "NO", "N/A"]

SUG_FIELDS = [
    "Closures","Brand","Name","URL","Address","Geocode","Phone","Hours",
    "Modern Category","Category","Included Parent","Good-to-know Tag",
    "Comment","New POI",
]

YES_NO = ["Yes","No","N/A"]

# Match CSV’s headers (incl. spaces & case)
COL_TICKET   = "Ticket type"
COL_LE       = "Last Editor Resolution"
COL_L1       = "L1 Resolution"
COL_L2       = "L2 Resolution"
COL_SUGF     = "Suggested fields"
COL_EDITED   = "Edited fields"
COL_OTHER    = "Other markings made along with procedural marking?"
COL_ISSUES   = "Are customer issues resolved?"
COL_ATTR_ERR = "Any attribute errors remain on the POI?"
COL_DISCREP  = "Are there still discrepancies between research indicators and POI data?"
COL_CUS1 = "All customer-suggested fields edited?"
COL_CUS2 = "All customer-suggested fields have a corresponding dependent edit?"


single_letters = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
double_letters = [f"{a}{b}" for a in single_letters for b in single_letters]
all_possible_cols = single_letters + double_letters


def expand_col_range(start, end):
    """ Expands a column range like 'AB-AI' to ['AB', 'AC', 'AD', ... 'AI']. """
    start_index = all_possible_cols.index(start)
    end_index = all_possible_cols.index(end)
    return all_possible_cols[start_index:end_index + 1]
# Preprocess the 'col' list and convert ranges
def preprocess_cols(col_list):
    expanded_cols = []
    for col in col_list:
        # Split by ',' first to handle multiple columns
        col_parts = col.split(',')
        for col_part in col_parts:
            col_part = col_part.strip().upper()
            if '-' in col_part:  # Handle ranges like "AB-AI"
                start_col, end_col = col_part.split('-')
                expanded_cols.extend(expand_col_range(start_col.strip(), end_col.strip()))
            else:
                expanded_cols.append(col_part.strip())
    return expanded_cols

def find_latest_report(directory='.'):
    csv_file = glob.glob(os.path.join(directory, "*.csv"))
    if not csv_file:
        return None
    latest_file = max(csv_file, key=os.path.getmtime)
    return latest_file

def load_config(csv_path: str):
    """
    Reads the config-format CSV and returns a dict with:
      - project_name, project_tab, quip_link
      - warnings_col, start_row
      - last_ran_date, last_avg_ticket_runtime, last_total_runtime
      - ids_type, last_id_row
    """
    df = pd.read_csv(csv_path, header=None, dtype=str).fillna('')
    
    # top-rows are single-value metadata
    project_name            = df.iat[0,1].strip() or None
    project_tab             = df.iat[1,1].strip() or None
    quip_link_raw           = df.iat[2,1].strip()
    quip_link               = f"https://quip-apple.com/{quip_link_raw}" if quip_link_raw else None
    warnings_col            = df.iat[3,1].strip().upper() or None
    start_row_txt           = df.iat[4,1].strip()
    start_row               = int(start_row_txt) if start_row_txt.isdigit() else None
    last_ran_date           = df.iat[5,1].strip() or None
    
    # numeric runtimes
    try:
        last_avg_ticket_runtime = float(df.iat[6,1])
    except ValueError:
        last_avg_ticket_runtime = None
    last_total_runtime       = df.iat[7,1].strip() or None

    # determine last non-blank ID row by dropping blank on col W (index 22)
    body = df.iloc[2:].reset_index(drop=True)
    body = body[body.iloc[:,22].astype(bool)]
    if not body.empty:
        last_idx_zero_based = body.index[-1]
        last_id_row = last_idx_zero_based + 4  # offset back to original CSV row
    else:
        last_id_row = None

    # ID type is in row 10 (i=9), col W (index 22)
    ids_type = df.iat[9,22].strip() or None

    return {
        "project_name": project_name,
        "project_tab": project_tab,
        "quip_link": quip_link,
        "warnings_col": warnings_col,
        "start_row": start_row,
        "last_ran_date": last_ran_date,
        "last_avg_ticket_runtime": last_avg_ticket_runtime,
        "last_total_runtime": last_total_runtime,
        "ids_type": ids_type,
        "last_id_row": last_id_row,
    }


if __name__ == "__main__":
    reporting_file = find_latest_report()
    if reporting_file is None:
        print("No reporting file found, process ended.")
        exit(1)

    df = pd.read_csv(reporting_file)
    print(f"Found latest report file to process at: {reporting_file}")

    total = len(df)
    print(f"total dataframe: {total}")


"""
# Counts & Percentages
def counts_and_pcts(col, items):
    cnts = [(df[col] == it).sum() for it in items]
    pcts = [f"{cnt/total*100:.2f}%" for cnt in cnts]
    return cnts, pcts

ticket_cnt, ticket_pct = counts_and_pcts(COL_TICKET, TICKET_TYPES)
le_cnt, le_pct = counts_and_pcts(COL_LE, LE_RES)
l1_cnt, l1_pct = counts_and_pcts(COL_L1, L1_RES)
l2_cnt, l2_pct = counts_and_pcts(COL_L2, L2_RES)
ALL_CUS1_cnt, ALL_CUS1_pct = counts_and_pcts(COL_CUS1, ALL_CUS1)
ALL_CUS2_cnt, ALL_CUS2_pct = counts_and_pcts(COL_CUS2, ALL_CUS2)

# SECTIONS
with open(REPORTING_CSV, "w", newline="") as f:
    w = csv.writer(f)

    w.writerow(["Total rows ran", total])
    w.writerow([])

# Section 1
    w.writerow([
        "Ticket type", "Count", "%", 
        "Last Editor Resolution", "Count", "%", 
        "L1 Resolution", "Count", "%", 
        "L2 Resolution", "Count", "%"
    ])

    rows1 = max(len(TICKET_TYPES), len(LE_RES), len(L1_RES), len(L2_RES))
    for i in range(rows1):
        row = []
        if i < len(TICKET_TYPES):
            row += [TICKET_TYPES[i], ticket_cnt[i], ticket_pct[i]]
        else:
            row += ["", "", ""]

        # Last Editor Resolution columns
        if i < len(LE_RES):
            row += [LE_RES[i], le_cnt[i], le_pct[i]]
        else:
            row += ["", "", ""]

        # L1 Resolution columns
        if i < len(L1_RES):
            row += [L1_RES[i], l1_cnt[i], l1_pct[i]]
        else:
            row += ["", "", ""]

        # L2 Resolution columns
        if i < len(L2_RES):
            row += [L2_RES[i], l2_cnt[i], l2_pct[i]]
        else:
            row += ["", "", ""]

        w.writerow(row)

    w.writerow([])  # separator

# Section 2
    w.writerow([
        "Suggested fields", "Count", "%",
        "Edited fields", "%",
        "Other markings made along with procedural marking?", "%",

    ])

    rows2 = max(len(ALL_CUS1), len(ALL_CUS2))
    for fld in SUG_FIELDS:
        c1 = (df[COL_SUGF]   == fld).sum()
        c2 = (df[COL_EDITED] == fld).sum()
        c3 = (df[COL_OTHER]  == fld).sum()

        w.writerow([
            fld,
            c1, f"{c1/total*100:.2f}%",
            c2, f"{c2/total*100:.2f}%",
            c3, f"{c3/total*100:.2f}%",

        ])

    w.writerow([])  #separator

# Section 3
    w.writerow([
        "Are customer issues resolved?", "Count", "%", 
        "Any attribute errors remain on the POI?", "Count", "%",
        "Are there still discrepancies between research indicators and POI data?", "Count", "%",
        "All customer-suggested fields edited?", "Count", "%",
        "All customer-suggested fields have a corresponding dependent edit?", "Count", "%",
    ])

    for v in YES_NO:
        c1 = (df[COL_ISSUES] == v).sum();   p1 = f"{c1/total*100:.2f}%"
        c2 = (df[COL_ATTR_ERR] == v).sum(); p2 = f"{c2/total*100:.2f}%"
        c3 = (df[COL_DISCREP] == v).sum();  p3 = f"{c3/total*100:.2f}%"
        c4 = (df[COL_CUS1] == v).sum();     p4 = f"{c4/total*100:.2f}%"
        c5 = (df[COL_CUS2] == v).sum();     p5 = f"{c5/total*100:.2f}%"

        w.writerow([
            v, c1, p1,    # Q1
            v, c2, p2,    # Q2
            v, c3, p3,    # Q3
            v, c4, p4,
            v, c5, p5 
        ])

print(f"✅  Written {REPORTING_CSV!r}")
"""