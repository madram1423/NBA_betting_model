import pandas as pd
import tls_client
from bs4 import BeautifulSoup
import requests
import random

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

