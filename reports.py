"""
Script to output a report based on Quip output
v1.1: instead of set variables read the cols to find all the possible options needed to output and find %s for
"""

RED = '\033[91m' # errors
GREEN = '\033[92m' # notes
YELLOW = '\033[93m' # warnings
MAGENTA = '\033[95m' # end of each loop iteration warning to verify
RESET = '\033[0m'

import csv
import pandas as pd

INPUT_CSV = "ICFI.csv"
REPORTING_CSV = "Report_Ticket.csv"

TICKET_TYPES = [
    "POI Datascience", "POI Change Details",
    "POI Remove",      "POI Add",
]
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
df    = pd.read_csv(INPUT_CSV)
total = len(df)

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
print(f":white_check_mark:  Written {REPORTING_CSV!r}")
