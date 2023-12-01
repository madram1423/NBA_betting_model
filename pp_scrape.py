# imports and scraping raw data from site
# df is the actual betting line
# df2 has other info, mostly using to get player id to name dict
from bs4 import BeautifulSoup as bs
import pandas as pd
import datetime as dt
from unidecode import unidecode
import time
import uuid
from betting_functions import get_url_json, update_csv_file


pp_url = "https://api.prizepicks.com/projections"

prizepicks = get_url_json(pp_url)

df = pd.json_normalize(prizepicks, record_path="data")

df2 = pd.json_normalize(prizepicks, record_path="included")
df2.drop(
    df2.columns[df2.columns.str.contains("unnamed", case=False)], axis=1, inplace=True
)

names = df2.loc[df2["type"] == "new_player"]
names = names[
    [
        "id",
        "attributes.name",
        "attributes.team",
        "attributes.league",
        "relationships.league.data.id",
    ]
]
new = df.merge(names, left_on="relationships.new_player.data.id", right_on="id")
new = new[
    [
        "attributes.description",
        "attributes.line_score",
        "attributes.start_time",
        "attributes.stat_type",
        "id_y",
        "attributes.name",
        "attributes.team",
        "attributes.league",
        "relationships.league.data.id_y",
    ]
]

df = new.rename(
    columns={
        "attributes.description": "opp",
        "attributes.line_score": "line",
        "attributes.stat_type": "stat",
        "attributes.team": "team",
        "attributes.league": "league_name",
        "relationships.league.data.id_y": "league_id",
        "attributes.start_time": "event_time",
        "attributes.name": "player",
        "id_y": "pp_player_id",
    }
)

full = df.copy(deep=True)
df["event_time"] = df["event_time"].apply(lambda x: pd.to_datetime(x, utc=True))
df["event_time"] = df["event_time"].dt.tz_convert("America/Chicago")
df["date"] = df["event_time"]
df["player"] = df["player"].apply(lambda x: unidecode(x).replace("_", " "))

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
    "3-PT Attempted": "3PA",
    "FG Made": "FG"
}
df = df.replace(syntax)
df.stat.unique()

df = df[df.stat != "Fantasy Score"]

df = df.replace("Fred VanVleet\t", "Fred VanVleet")
df = df.replace("Nicolas Claxton", "Nic Claxton")
df = df.replace("Robert Williams III", "Robert Williams")
df = df.replace("LeBron James\t", "LeBron James")
df = df.replace("KJ Martin Jr.", "Kenyon Martin Jr.")
df = df.replace("Xavier Tillman", "Xavier Tillman Sr.")
df = df.reset_index(drop=True)

today = dt.datetime.today()
df["scrape_time"] = df["scrape_time"] = dt.datetime.now().replace(microsecond=0, second=0)
df.columns = [x.lower() for x in df.columns]


def create_uuid_from_columns(row):
    seed = f"{row['player']}_{row['stat']}_{pd.to_datetime(row['event_time']).floor('h')}"
    id = uuid.uuid5(uuid.NAMESPACE_DNS, seed)
    return str(id)[0:10]

df['event_time'] = pd.to_datetime(df['event_time']).dt.floor('h')
df["prop_id"] = df.apply(create_uuid_from_columns, axis=1)
df = df[
    [
        "player",
        "team",
        "line",
        "stat",
        "opp",
        "league_id",
        "league_name",
        "event_time",
        "pp_player_id",
        "date",
        "scrape_time",
        "prop_id",
    ]
]

df["scrape_time"] = pd.to_datetime(df["scrape_time"]).dt.tz_localize('US/Central')
pp_path = f"Lines/pp/pp_{today.year}_{today.month}_{today.day}.csv"
print(df.sample(5))
update_csv_file(df, pp_path)
print("Success!")