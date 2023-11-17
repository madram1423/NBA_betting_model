import random
import pandas as pd
import streamlit as st
acronyms = pd.read_csv("acronyms.csv", index_col=0)
standings = pd.read_csv("data/current_standings.csv")
east = standings["East"].to_list()
west = standings["West"].to_list()
standings_list = [west,east]

shared_preds = [
    ["DEN", "GSW", "PHX", "LAL", "SAC", "LAC", "MEM", "DAL"],
    ["MIL", "BOS", "CLE", "PHI", "NYK", "MIA", "NYK", "BKN"],
]

cam_preds = [
    random.sample(west,8),
    random.sample(east,8)
]

austy_preds = [
    random.sample(west,8),
    random.sample(east,8)
]

def compute_score(pred_rank, actual_rank):
    diff = abs(pred_rank - actual_rank)
    if diff == 0:
        return 3
    elif diff == 1:
        return 2
    elif diff == 2:
        return 1
    return 0


def get_scores(user_pred, current_standings):
    scores = []
    for conf in [0,1]:
        for rank, team in enumerate(user_pred[conf]):
            res = compute_score(rank, current_standings[conf].index(team))
            scores.append(res)
    return scores

shared_score = get_scores(shared_preds, standings_list)
austy_score = get_scores(austy_preds, standings_list)
cam_score = get_scores(cam_preds, standings_list)

def get_player_standing_df(preds,scores):
    df = pd.DataFrame(preds).T
    df.columns= ['West','East']
    df['  '] = scores[0:8]
    df[' '] = scores[8:]
    df.index = [1,2,3,4,5,6,7,8]
    return df[['West','  ','East',' ']]

shared_df = get_player_standing_df(shared_preds,shared_score)
cam_df = get_player_standing_df(cam_preds,cam_score)
austy_df = get_player_standing_df(austy_preds,austy_score)
current_df = pd.DataFrame((west[0:8],east[0:8])).T
current_df.index = [1,2,3,4,5,6,7,8]
current_df.columns = ['West','East']

standings = pd.concat((current_df,shared_df,cam_df,austy_df),axis=1,keys=['Actual','Shared','Cam','Austy'])
print(standings)
st.dataframe(standings)
st.write('Shared score', sum(shared_score))
st.write('Cam score', sum(austy_score))
st.write('Austy score', sum(cam_score))