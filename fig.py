import pandas as pd
import plotly.express as px

df = pd.read_csv("results.csv")
new_df = df.sort_values(by=["recorded_date"])[:-8]

ag = new_df.groupby("first_grantee").agg('count').reset_index()

fig = px.bar(ag, x='first_grantee', y='recorded_date')
fig.show()
