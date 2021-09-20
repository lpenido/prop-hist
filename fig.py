import sqlite3
import pandas as pd
import plotly.express as px

df = pd.read_csv("results.csv")
new_df = df.sort_values(by=["recorded_date"])[:-8]

ag = new_df.groupby("type_desc").agg('count').reset_index()

fig = px.bar(ag, x='type_desc', y='recorded_date')
fig.show()

# con = sqlite3.connect("records.db")
# df = pd.read_sql_query("SELECT * from records;", con)

# print(df.head())
# print(len(df.pin.unique()))

# df.to_csv("bout_50_pins.csv", index=False)
# breakpoint()