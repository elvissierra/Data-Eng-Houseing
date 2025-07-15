import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import io
directory = "csv_files/Analytics_Report.csv"
#df = sns.load_dataset("csv_files/penguins.csv")
with open(directory, 'r') as f:
    content = f.read()
sections = [s.strip() for s in content.split("\n\n") if s.strip()]
for section in sections:
    rows = section.splitlines()
    if len(rows) < 2:
        continue
    data = "\n".join(rows)
    try:
        df_section = pd.read_csv(io.StringIO(data))
        if "Count" in df_section.columns:
            df_section.plot(x=df_section.columns[0], y="Count", kind="barh")
        elif "Duplicate" in df_section.columns:
            df_section.plot(x=df_section.columns[0], y ="Duplicate", kind="pie")
        elif "Average" in df_section.columns:
            df_section.plot(x=df_section.columns[0], y ="Average", kind="hexbin")
    except pd.errors.EmptyDataError:
        continue