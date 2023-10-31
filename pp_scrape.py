# imports and scraping raw data from site
# df is the actual betting line
# df2 has other info, mostly using to get player id to name dict
from bs4 import BeautifulSoup as bs
import pandas as pd
import datetime as dt
from unidecode import unidecode
import uuid
from betting_functions import get_url_json,update_csv_file


pp_url = "https://api.prizepicks.com/projections"

prizepicks = get_url_json(pp_url)

df = pd.json_normalize(prizepicks, record_path="data")

df2 = pd.json_normalize(prizepicks, record_path="included")
df2.drop(
    df2.columns[df2.columns.str.contains("unnamed", case=False)], axis=1, inplace=True
)

names = df2[["type", "id", "attributes.name"]]
names = names.loc[names["type"] == "new_player"]
names = names[["id", "attributes.name"]]

name = names["attributes.name"].tolist()
id = names["id"].tolist()

names_dict = {id[i]: name[i] for i in range(len(name))}

ids = df["relationships.new_player.data.id"].unique()

base = df[:-1]
# trimming excess columns and adding actual player names
df = base[
    [
        "attributes.description",
        "attributes.line_score",
        "attributes.stat_type",
        "relationships.new_player.data.id",
        "relationships.league.data.id",
        "attributes.start_time",
    ]
]

df["Player"] = df["relationships.new_player.data.id"].map(names_dict)
df = df[
    [
        "Player",
        "attributes.description",
        "attributes.line_score",
        "attributes.stat_type",
        "relationships.league.data.id",
        "attributes.start_time",
    ]
]

df = df.rename(
    columns={
        "attributes.description": "Team",
        "attributes.line_score": "Line",
        "attributes.stat_type": "Stat",
        "relationships.league.data.id": "League",
        "attributes.start_time": "Date",
    }
)

full = df.copy(deep=True)

df["Date"] = df["Date"].apply(lambda x: pd.to_datetime(x,utc=True))
df["Date"] = df["Date"].dt.tz_convert('America/Chicago')
df['event_time'] = df['Date']
df["Player"] = df["Player"].apply(lambda x: unidecode(x).replace("_", " "))

syntax = {
    "Points": "PTS",
    "Rebs": "TRB",
    "Asts": "AST",
    "Rebounds": "TRB",
    "3-PT Made": "3P",
    "Assists": "AST",
    "Turnovers": "TOV",
    "Blks": "BLK",
    "Pts": "PTS",
    "Pts+Asts": "PTS+AST",
    "Pts+Rebs+Asts": "PTS+TRB+AST",
    "Pts+Rebs": "PTS+TRB",
    "Rebs+Asts": "TRB+AST",
    "Blks+Stls": "BLK+STL",
    "Stls": "STL",
    "Free Throws Made": "FT",
    "Blocked Shots": "BLK",
    "Steals": "STL",
    "Personal Fouls": "PF",
    "FG Attempted": "FGA",
    "Offensive Rebounds": "ORB",
    "Defensive Rebounds": "DRB",
    "3-PT Attempted": '3PA'
}
df = df.replace(syntax)
df.Stat.unique()

df = df[df.Stat != "Fantasy Score"]

df = df.replace("Fred VanVleet\t", "Fred VanVleet")
df = df.replace("Nicolas Claxton", "Nic Claxton")
df = df.replace("Robert Williams III", "Robert Williams")
df = df.replace("LeBron James\t", "LeBron James")
df = df.replace("KJ Martin Jr.", "Kenyon Martin Jr.")
df = df.replace("Xavier Tillman", "Xavier Tillman Sr.")
df = df.reset_index(drop=True)

today = dt.datetime.today()
df["time"] = df['time'] = dt.datetime.now().replace(microsecond=0,second=0)
df.columns = [x.lower() for x in df.columns]

def create_uuid_from_columns(row):
    seed = f"{row['player']}_{row['stat']}_{row['event_time']}"
    id = uuid.uuid5(uuid.NAMESPACE_DNS, seed)
    return str(id)[0:10]

df['prop_id'] = df.apply(create_uuid_from_columns, axis=1)


pp_path = f"Lines/pp/pp_{today.year}_{today.month}_{today.day}.csv"
print(df.head(10))
update_csv_file(df,pp_path)

