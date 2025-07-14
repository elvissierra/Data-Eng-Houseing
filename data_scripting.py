import pandas as pd


files = ("file1", "file2", "file3", "file4", "file5")
file_count = ("1st", "2nd", "3rd", "proceeding")

for i, f in enumerate(files):
    if i == 0:
        print(f"This is the {file_count[0]}:", f)
    elif i == 1:
        print(f"This is the {file_count[1]}:", f)
    elif i == 2:
        print(f"This is the {file_count[2]}:", f)
    else:
        print(f"These are the {file_count[3]}:", f)

