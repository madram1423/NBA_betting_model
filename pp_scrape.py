# imports and scraping raw data from site
# df is the actual betting line
# df2 has other info, mostly using to get player id to name dict
from bs4 import BeautifulSoup as bs
import pandas as pd
import datetime as dt
import requests
import tls_client
from unidecode import unidecode
import sys


headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "sec-ch-ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Google Chrome";v="114"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
}

requests = tls_client.Session(
    client_identifier="chrome112",
)

response1 = requests.get("https://api.prizepicks.com/projections")

prizepicks = response1.json()

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

# df = df.loc[df.League=='7']
df["Date"] = df["Date"].apply(lambda x: x.split("T")[0])
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

nba = df.loc[df.league == "7"]
nba.to_csv(f"Lines/nba_lines_{today.year}_{today.month}_{today.day}.csv")
df.to_csv(f"Lines/full_lines_{today.year}_{today.month}_{today.day}.csv")
print(df.head(10))
