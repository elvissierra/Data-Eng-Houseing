import pandas as pd

#1
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


#2 Perform Schema Validation
from pyspark.sql.types import StructType, StructField, IntegerType, StringType
schema = StructType([
    StructField("id", IntegerType(), True),
    StructField("name", StringType(), True),
    StructField("age", IntegerType(), True)
])
df = spark.read.schema(schema).csv("path_to_file.csv")
if df.schema == schema:
    print("Schema validated")


#3 Remove Duplicates
deduped_df = df.dropDuplicates()
deduped_df.show()


#4 Handle Null Values
cleaned_df = df.fillna({"age": 0, "name": "Unknown"})
cleaned_df.show()


#5 Calculate Moving Averages
from pyspark.sql.window import Window
import pyspark.sql.functions as F

window = Window.partitionBy().orderBy("date")
df = df.withColumn("moving_avg", F.avg("value").over(window))
df.show()


#6 Join DataFrames
joined_df = df1.join(df2, df1.id == df2.id, "inner")
joined_df.show()


#7 Extract Transformation Load (ETL) Pipeline
def etl_pipeline(input_path, output_path):
    df = spark.read.csv(input_path, header=True)
    transformed_df = df.withColumn("new_column", F.lit("value"))
    transformed_df.write.csv(output_path, mode="overwrite")
etl_pipeline("input.csv", "output/")


#8 Write Data to Azure Data Lake
output_path = "abfs://container@account.dfs.core.windows.net/output/"
df.write.parquet(output_path, mode="overwrite")


#9 Create Partitioned Tables
df.write.partitionBy("year", "month").parquet("output_path", mode="overwrite")


#10 Aggregate Data
aggregated_df = df.groupBy("category").agg(F.sum("value").alias("total"))
aggregated_df.show()


#11 Detect File Duplicates by Name
from pyspark.sql.functions import col
files_df = spark.read.csv("files_metadata.csv", header=True)
duplicate_files = files_df.groupBy("filename").count().filter(col("count") > 1)
duplicate_files.show()


#12 Generate Reports
report = df.groupBy("category").agg(F.count("*").alias("count"))
report.coalesce(1).write.csv("report.csv", header=True, mode="overwrite")


#13 Filter Data by Date
filtered_df = df.filter((F.col("date") >= "2024-01-01") & (F.col("date") <= "2024-12-31"))
filtered_df.show()


#14 Create Temporary Views for SQL
df.createOrReplaceTempView("data_view")
spark.sql("SELECT * FROM data_view WHERE value > 100").show()


#15 Merge DataFrames
merged_df = df1.union(df2)
merged_df.show()


#16 Trigger Notifications for Data Quality Issues
if df.filter(F.col("value").isNull()).count() > 0:
    print("Data Quality Issue: Null values detected.")


#17 Write Data to Snowflake
df.write \
    .format("snowflake") \
    .options(**snowflake_options) \
    .save()


#18 Compress Output Files
df.write.csv("output/", mode="overwrite", compression="gzip")


#19 Analyze Logs
logs_df = spark.read.text("path_to_logs/")
logs_df.filter(logs_df.value.contains("ERROR")).show()


#20 Automate File Archiving
from datetime import datetime
archive_path = f"archive/{datetime.now().strftime('%Y%m%d')}/"
df.write.csv(archive_path, mode="overwrite")


#21 Read data in file
import pandas as pd

directory = "csv_files/"

def read_data(directory):

    data = pd.read_csv(directory)
    return data

file = read_data(directory + "report_config.csv")
print(file.head())

#22 SQL solutions
https://github.com/dataquestio/solutions/blob/master/600Solutions.sql


#23 Visualize Data with Seaborn
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


#24    