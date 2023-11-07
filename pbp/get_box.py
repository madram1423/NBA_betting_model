import requests
import json
import pandas as pd
import numpy as np
import datetime as dt
import os.path


def get_box_score(box_url,headers,game_id):

    r= requests.get(box_url, headers=headers, timeout = 7)
    data = json.loads(r.text)
    box = pd.DataFrame.from_dict(data['resultSets'][0]['rowSet'])
    col_names = data['resultSets'][0]['headers']
    box.columns = col_names
    box.columns = box.columns.str.lower()
    box.to_csv(f'pbp/box_scores/box_{game_id}.csv')
    return box

game_ids = pd.read_csv('pbp/game_ids.csv',dtype={'game_id':'str'})
#dubs = game_ids.loc[(game_ids.home=='GSW') | (game_ids.away=='GSW')]['game_id'].to_list()

season_type = 'Regular+Season'

failed = []
for n in range(len(game_ids)):  #range(len(game_ids)):
    game_id = game_ids.loc[n,'game_id']
    path = f'pbp/box_scores/box_{game_id}.csv'
    year = game_ids.loc[n,'season']
    season = '20'+str(year-1)+'-'+str(year)
    print(game_id)
    if not os.path.isfile(path):
        try:
            start_range = '0'
            box_url = f'https://stats.nba.com/stats/boxscoretraditionalv2?EndPeriod=10&EndRange=28800&GameID={game_id}&RangeType=0&Season=20{year-1}-{year}&SeasonType={season_type}&StartPeriod=1&StartRange={start_range}'
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36', 'x-nba-stats-origin': 'stats', 'x-nba-stats-token': 'true', 'Host':'stats.nba.com', 'Referer':f'https://stats.nba.com/game/{game_id}/'}
            get_box_score(box_url,headers,game_id)
        except:
            failed.append(game_id)
            print(game_id+'failed')
failed_ids = pd.DataFrame(failed)
failed_ids.to_csv('box_failed_ids.csv',index=False)