# Environment
from dotenv import load_dotenv
load_dotenv()

import os 
import pandas as pd
import sqlite3
import seaborn as sns
import matplotlib.pyplot as plt

sns.set_theme(style="whitegrid")
sns.set_context("paper", font_scale=1) 

sql = """
SELECT * FROM records;
"""
db = os.environ.get("DB")
with sqlite3.connect(db) as conn:
    df = pd.read_sql(sql, conn)

table = pd.pivot_table(df, 
    values = ["id", "pin"], 
    index = ["first_grantor"], 
    aggfunc = {
        "id": "count",
        'pin': pd.Series.nunique
    }
)
table.reset_index(inplace=True)
table = table.sort_values(by=["id"])

g = sns.catplot(x="first_grantor", y="id", kind="bar", color="b", data=table[-15:], height=2, aspect=16/4)

g.set_xticklabels(rotation=90)
plt.title("Top 15 Property Record Parties")
plt.ylabel("Property Record Filings")
plt.xlabel("Record Filer")

figure_name = os.path.join(os.environ.get("FIGS"),"figure1.png")
plt.savefig(figure_name)

plt.show()
