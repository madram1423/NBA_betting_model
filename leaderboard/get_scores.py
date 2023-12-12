import random
import pandas as pd
import streamlit as st
import pandas as pd
import tls_client
from bs4 import BeautifulSoup
import requests
from leaderboard import get_standings
acronyms = pd.read_csv("reference_data/acronyms.csv", index_col=0)

requests = tls_client.Session(
    client_identifier="chrome112",
)

def get_standings():
    acronyms = pd.read_csv('./reference_data/acronyms.csv',index_col=0)
    acr_dict = {}
    for i in range(len(acronyms)):
        acr_dict[acronyms.Team[i]] = acronyms.Acr[i]


    url = 'https://www.basketball-reference.com/leagues/NBA_2024_standings.html'
    response1 = requests.get(url)
    soup = BeautifulSoup(response1.content)

    # use findALL() to get the column headers
    soup.findAll('tr', limit=40)
    # use getText()to extract the text we need into a list
    i = 0
    header_list = []
    length = 35
    while i < length:
        headers = [th.getText() for th in soup.findAll('tr', limit=length)[i].findAll('th')]
        i = i +1
        if headers:
            header_list.append(headers[0])
            idx = i
    print(headers)
    east,west = [],[]
    for team in header_list:
        team = team.replace('*','')
        team = team.split('\xa0')[0]
        if team =='Eastern Conference':
            flag = 0
        if team =='Western Conference':
            flag = 1
        if flag == 0 and team !='Eastern Conference':
            east.append(acr_dict[team])
        if flag == 1 and team !='Western Conference':
            west.append(acr_dict[team])



    df = pd.DataFrame([east,west]).T
    df.columns = ['East','West']
    return df


standings = get_standings()
#standings = pd.read_csv("data/current_standings.csv")
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
st.title('Current Standings vs Predicted Standings')
st.dataframe(standings)
st.header('Current Scores')
st.write('Shared score', sum(shared_score))
st.write('Cam score', sum(austy_score))
st.write('Austy score', sum(cam_score))