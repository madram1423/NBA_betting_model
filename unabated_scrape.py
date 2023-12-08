# imports and scraping raw data from site
# df is the actual betting line
# df2 has other info, mostly using to get player id to name dict
# from scipy.stats import poisson
import pandas as pd
import numpy as np
import datetime as dt
from betting_functions import *
import uuid
import os
import random

id = uuid.uuid5(uuid.NAMESPACE_DNS,str(random.random()))
unabated_url = f"https://content.unabated.com/markets/b_playerprops.json?uuid=f{str(id)}"
data = get_url_json(unabated_url)


# team from id dict
teamtemp = pd.json_normalize(data["teams"], max_level=0)
teams = pd.DataFrame()
for league_code in range(len(teamtemp.T)):
    teams = pd.concat((teams, pd.json_normalize(teamtemp.iloc[0, league_code])))
teams = teams[["abbreviation", "id"]]
teamdict = dict(zip(teams.id, teams.abbreviation))

# bookie from id dict
bookies = pd.json_normalize(data["marketSources"])
id2book = dict(list(zip(bookies.id, bookies.name)))

# player json normalize
people_raw = pd.json_normalize(data["people"], max_level=0)
ppl = pd.DataFrame()
for i in range(len(people_raw.T)):
    y = pd.json_normalize(people_raw.T.iloc[i])
    ppl = pd.concat((ppl, y))

i2p = dict(zip(ppl.id, (ppl.firstName + " " + ppl.lastName)))

# step 1 of json normalize for lines
df = pd.json_normalize(data["propsPeopleEvents"], max_level=0)
lines_df = pd.json_normalize(df.iloc[0, 0])

lines_df = pd.DataFrame()
for league_code in df.columns:
    df_temp = pd.json_normalize(df.loc[0, league_code], max_level=0)
    df_temp["league_id"] = league_code.split(":")[0].split("g")[-1]
    lines_df = pd.concat((lines_df, df_temp)).reset_index(drop=True)


lines_df["person_name"] = lines_df.personId.apply(lambda x: i2p[x])

# replacing team id with team name
teams = pd.json_normalize(lines_df.eventTeams)
teams[["1.id", "0.id"]]
teams["home"] = teams["1.id"].apply(lambda x: teamdict[x])
teams["away"] = teams["0.id"].apply(lambda x: teamdict[x])
teams = teams[["home", "away"]]

# renaming stats
bt2stat = {
    "bt77": "TRB",
    "bt73": "PTS",
    "bt69": "3P",
    "bt78": "TRB+AST",
    "bt74": "PTS+AST",
    "bt75": "PTS+TRB",
    "bt76": "PTS+TRB+AST",
    "bt70": "AST",
    "bt84": "TO",
    "bt82": "BLK+STL",
    "bt81": "STL",
    "bt71": "BLK",
    "bt72": "Techs",
    "bt83": "Triple Double",
    "bt85": "Total Hits",
    "bt19": "Total Bases",
    "bt17": "Pitcher Strikeouts",
    "bt18": "Home Runs",
    "bt12": "Rush Yards",
    "bt16": "Receiving Yards",
    "bt68": "Rush+Rec Yards",
    "bt11": "Rushing Attempts",
    "bt56": "Sacks",
    "bt67": "Rush Attempts",
    "bt61": "Longest Pass Completion",
    "bt57": "Tackles+Ast",
    "bt62": "INT",
    "bt59": "FG",
    "bt58": "Extra Points Made",
    "bt60": "Kicking Points",
    "bt65": "Pass Touchdowns",
    "bt63": "Pass Attempts",
    "bt13": "Pass Completions",
    "bt14": "Pass Yards",
    "bt64": "Pass+Rush Yds",
    "bt15": "Receptions",
    "bt66": "Longest Reception",
}



def get_odds(row):
    side_dict = {"si0": "over", "si1": "under"}
    event_time = lines_df.eventStart[row]
    person_id = lines_df.personId[row]
    person_name = lines_df.person_name[row]
    league = lines_df.league_id[row]
    player_json = lines_df["propsMarketSourcesLines"][row]
    player_keys = player_json.keys()
    test_list = []
    for (
        key
    ) in (
        player_keys
    ):  # key is something like 'si1:ms8:an0'  where the first chunk is 1 or 0 meaning over or under, middle chunk is bookie id
        for stat_id in player_json[key]:
            book = key.split(":")[1][2:]
            book_name = id2book.get(int(book), "idk")
            side = np.where(key.split(":")[0] == "si0", "over", "under")
            side = side_dict.get(key.split(":")[0], "N/A")
            stat = bt2stat.get(stat_id, stat_id)
            price = player_json[key][stat_id]["americanPrice"]
            points = player_json[key][stat_id]["points"]
            test_list.append([points, price, side, stat, book_name, league, event_time])
            # points, price, side, stat, book
    results_df = pd.DataFrame(test_list)
    results_df.columns = [
        "points",
        "price",
        "side",
        "stat",
        "book",
        "league_id",
        "event_time",
    ]
    results_df["player"] = person_name
    results_df["player_id"] = person_id
    results_df = results_df[
        [
            "player",
            "player_id",
            "points",
            "price",
            "side",
            "stat",
            "book",
            "league_id",
            "event_time",
        ]
    ].dropna()
    results_df["prob"] = results_df["price"].apply(
        lambda x: (-x / (100 - x)) if x < 0 else 100 / (x + 100)
    )
    team = teamdict.get(lines_df.teamId.iloc[row])
    results_df['team'] = team
    if team == teams["home"][row]:
        results_df['opp'] = teams["away"][row]
        results_df['home'] = 1
    else:
        results_df['opp'] = teams["home"][row]
        results_df['home'] = 0
        
    return results_df


# getting lines for every player
odds = pd.DataFrame()
for i in range(len(lines_df)):
    if i % 20 == 0:
        print(i, "/", len(lines_df))
    odds = pd.concat((odds, get_odds(i)))

print(odds.iloc[0])
# bookmaker is broken right now
# not sure how to handle Total Bases because it isn't poisson
now = dt.datetime.now().replace(microsecond=0, second=0)
today = dt.datetime.today()
odds = odds.loc[odds.book != "Bookmaker"]
odds = odds.loc[~((odds.stat == "Total Bases") & (odds.points == 1.5))]
odds["time"] = now
odds["time"] = pd.to_datetime(odds["time"]).dt.tz_localize('US/Central')

odds["event_time"] = odds["event_time"].apply(lambda x: pd.to_datetime(x, utc=True))
odds["event_time"] = odds["event_time"].dt.tz_convert("America/Chicago")


def create_uuid_from_columns(row):
    seed = f"{row['player']}_{row['stat']}_{pd.to_datetime(row['event_time']).floor('h')}"
    id = uuid.uuid5(uuid.NAMESPACE_DNS, seed)
    return str(id)[0:10]


odds["prop_id"] = odds.apply(create_uuid_from_columns, axis=1)





raw_file_path = (
    f"Lines/unabated/unabated_raw_{today.year}_{today.month}_{today.day}.csv"
)
update_csv_file(odds, raw_file_path)


# getting probabilities to hit every posted line for every player
# probably could use more optimization

columns = [
    "prop_id",
    "Player",
    "Stat",
    "Line",
    "o_Prob",
    "u_Prob",
    "num_books",
    "means",
]
players = odds.player.unique()

odds_agg = (
    odds.groupby(
        [
            "prop_id",
            "player",
            "player_id",
            "side",
            "points",
            "stat",
            "league_id",
            "event_time",
            "opp",
            "team",
        ],
        as_index=False,
    )["prob"]
    .agg(func=["mean", "count"])
    .reset_index()
)

odds_condensed = odds_agg.pivot(
    index=[
        "prop_id",
        "player",
        "player_id",
        "points",
        "stat",
        "league_id",
        "event_time",
        "opp",
        "team",
        "count",
    ],
    columns="side",
    values="mean",
).reset_index()
odds_condensed.rename(
    columns={"over": "over_prob", "under": "under_prob", "points": "line"}, inplace=True
)
odds_condensed["total"] = odds_condensed["over_prob"] + odds_condensed["under_prob"]
odds_condensed["over_prob"] = odds_condensed["over_prob"] / odds_condensed["total"]
odds_condensed["under_prob"] = odds_condensed["under_prob"] / odds_condensed["total"]
odds_condensed.drop("total", axis=1, inplace=True)
odds_condensed["mean_pred"] = odds_condensed.apply(
    lambda row: prob2mean(row["over_prob"], row["line"], "over"), axis=1
)


def weighted_average(group):
    weighted_sum = (group["mean_pred"] * group["count"]).sum()
    total_weight = group["count"].sum()
    return weighted_sum / total_weight


# Group by 'player' and 'stat', and apply the custom function
temp_table = (
    odds_condensed.groupby(["prop_id"]).apply(weighted_average).reset_index(name="pred")
)
final_odds = odds_condensed.merge(temp_table, on=["prop_id"])
final_odds.drop("mean_pred", inplace=True, axis=1)


today = dt.datetime.today()
timestamp = dt.datetime.now().replace(microsecond=0, second=0)
final_odds["scrape_time"] = now
final_odds["scrape_time"] = pd.to_datetime(final_odds["scrape_time"]).dt.tz_localize('US/Central')

final_odds = final_odds.reset_index(drop=True)
final_file_path = f"Lines/unabated/unabated_{today.year}_{today.month}_{today.day}.csv"
update_csv_file(final_odds, final_file_path)

print("Success!")
