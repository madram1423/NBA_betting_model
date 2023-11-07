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


def get_pbp(pbp_url,headers):

    r= requests.get(pbp_url, headers=headers, timeout = 7)
    data = json.loads(r.text)
    pbp = pd.DataFrame.from_dict(data['resultSets'][0]['rowSet'])
    col_names = data['resultSets'][0]['headers']
    pbp.columns = col_names
    pbp.columns = pbp.columns.str.lower()
    pbp_times = pbp['pctimestring'].str.split(':', expand=True)
    pbp_times[0] = pbp_times[0].astype(str).astype(int)
    pbp_times[1] = pbp_times[1].astype(str).astype(int)
    pbp['timeinseconds'] = (pbp_times[0]*60) + pbp_times[1]
    pbp['play_elapsed_time'] = pbp['timeinseconds'].shift(1) - pbp['timeinseconds'] 
    pbp['play_elapsed_time'] = pbp['play_elapsed_time'].fillna(0)
    pbp['play_elapsed_time'] = np.where(pbp['period'] != pbp['period'].shift(1), 0, pbp['play_elapsed_time'])
    pbp['total_elapsed_time'] = pbp.groupby(['game_id'])['play_elapsed_time'].cumsum()
    pbp['max_time'] = pbp.groupby('game_id')['play_elapsed_time'].transform('sum')
    pbp['time_remaining'] = pbp['max_time'] - pbp['total_elapsed_time']
    pbp['scoremargin'] = np.where(pbp['scoremargin']=='TIE',0,pbp['scoremargin'])
    pbp['scoremargin'] = pbp['scoremargin'].fillna(0).astype(int)
    pbp = pbp[['game_id', 'eventnum', 'eventmsgtype', 'eventmsgactiontype', 'period',
        'pctimestring', 'homedescription', 'neutraldescription',
        'visitordescription', 'score', 'scoremargin',
        'player1_id', 'player1_name', 'player1_team_abbreviation',
        'player2_id', 'player2_name', 'player2_team_abbreviation',
        'player3_id', 'player3_name', 'player3_team_abbreviation',
        'timeinseconds', 'play_elapsed_time',
        'total_elapsed_time', 'max_time', 'time_remaining']]
    return pbp


def getQuarterStarters(quarter):
    if quarter == 1:
        start_range = 0
        end_range = 50
    elif quarter == 2:
        start_range = 7201
        end_range = 7493
    elif quarter == 3:
        start_range = 14410
        end_range = 14840
    elif quarter == 4:
        start_range = 21621
        end_range = 21913
        
    starters_url = f'https://stats.nba.com/stats/boxscoretraditionalv2?EndPeriod=14&GameID={game_id}&RangeType=2&Season={season}&SeasonType={season_type}&StartPeriod=1&StartRange={str(start_range)}&EndRange={str(end_range)}'
    r= requests.get(starters_url, headers=headers, timeout = 7)
    data = json.loads(r.text)
    starters = pd.DataFrame.from_dict(data['resultSets'][0]['rowSet'])
    col_names = data['resultSets'][0]['headers']
    starters.columns = col_names
    starters.columns = starters.columns.str.lower()
    return starters[['game_id', 'team_id', 'team_abbreviation', 'player_id',
       'player_name']]


class Game():
    def __init__(self,game_id,pbp_url,box_url,headers):
        self.pbp = get_pbp(pbp_url,headers=headers)
        self.box = get_box_score(box_url,headers=headers,game_id=game_id)
        self.hteam = self.box.team_abbreviation.unique()[1]
        self.ateam = self.box.team_abbreviation.unique()[0]
        self.pbp['h_lineup'] = ''
        self.pbp['a_lineup'] = ''
        
        
    def compute_lineups(self):
        #getting starters from boxscore df
        print('home',self.hteam,'away',self.ateam)
        self.h_starters = self.box.loc[(self.box.start_position != '') & 
                                       (self.box.team_abbreviation == self.hteam)].reset_index()['player_id'].to_list()
        self.h_starters = sorted(self.h_starters)
        self.a_starters = self.box.loc[(self.box.start_position != '') & 
                                       (self.box.team_abbreviation == self.ateam)].reset_index()['player_id'].to_list()
        self.a_starters = sorted(self.a_starters)
        #assigning starters to lineup for start of game
        self.pbp.at[0,'h_lineup'] = self.h_starters
        self.pbp.at[0,'a_lineup'] = self.a_starters
        self.pbp.at[1,'h_lineup'] = self.h_starters
        self.pbp.at[1,'a_lineup'] = self.a_starters
        #assigning quarter starters from quarter box scores
        for idx, row in self.pbp.iterrows():
            if row.pctimestring == '12:00' and row.period != 1:
                qstart = getQuarterStarters(row.period)
                qstart_h = qstart.loc[qstart.team_abbreviation == self.hteam]
                qstart_a = qstart.loc[qstart.team_abbreviation != self.hteam]
                self.pbp.at[idx,'h_lineup'] = sorted(qstart_h.player_id.to_list())
                self.pbp.at[idx,'a_lineup'] = sorted(qstart_a.player_id.to_list())
        
        prev_h_lineup = self.h_starters.copy()  # Initialize with the starting lineup
        prev_a_lineup = self.a_starters.copy()  # Initialize with the starting lineup

        for idx, row in self.pbp.iterrows():
            if row.pctimestring == '12:00' and row.period == 1:
                h_lineup = sorted(self.h_starters)
                a_lineup = sorted(self.a_starters)

            elif row.pctimestring == '12:00' and row.period != 1:
                h_lineup = sorted(row['h_lineup'])  # Use the existing lineup for the beginning of the quarter
                a_lineup = sorted(row['a_lineup'])  # Use the existing lineup for the beginning of the quarter
            else:
                h_lineup = prev_h_lineup.copy()  # Create a copy of the previous h_lineup
                a_lineup = prev_a_lineup.copy()  # Create a copy of the previous a_lineup

                if isinstance(row['homedescription'], str) and row['homedescription'].startswith('SUB'):
                    try:
                        h_lineup.remove(row['player1_id'])
                        h_lineup.append(row['player2_id'])
                    except:
                        print(row.player1_id,row.player2_id,h_lineup,row.pctimestring,row.period)

                if isinstance(row['visitordescription'], str) and row['visitordescription'].startswith('SUB'):
                    try:
                        a_lineup.remove(row['player1_id'])
                        a_lineup.append(row['player2_id'])
                    except:
                        print(row.player1_id,row.player2_id,a_lineup,row.pctimestring,row.period)

            self.pbp.at[idx, 'h_lineup'] = sorted(h_lineup)
            self.pbp.at[idx, 'a_lineup'] = sorted(a_lineup)
            prev_h_lineup = h_lineup  # Update the previous h_lineup for the next iteration
            prev_a_lineup = a_lineup  # Update the previous a_lineup for the next iteration
        self.pbp['a_lineup'] = self.pbp['a_lineup'].apply(lambda x: tuple(x))
        self.pbp['h_lineup'] = self.pbp['h_lineup'].apply(lambda x: tuple(x))
        return 

import os
game_ids = pd.read_csv('pbp/game_ids.csv',dtype={'game_id':'str'})
#dubs = game_ids.loc[(game_ids.home=='GSW') | (game_ids.away=='GSW')]['game_id'].to_list()

season_type = 'Regular+Season'

failed = []
for n in range(len(game_ids)):  #range(len(game_ids)):
    game_id = game_ids.loc[n,'game_id']
    path = f'pbp/pbp_raw/{game_id}_pbp.csv'
    year = game_ids.loc[n,'season']
    season = '20'+str(year-1)+'-'+str(year)
    print(game_id)
    if not os.path.isfile(path):
        try:
            start_range = '0'
            box_url = f'https://stats.nba.com/stats/boxscoretraditionalv2?EndPeriod=10&EndRange=28800&GameID={game_id}&RangeType=0&Season=20{year-1}-{year}&SeasonType={season_type}&StartPeriod=1&StartRange={start_range}'
            pbp_url = f'https://stats.nba.com/stats/playbyplayv2?EndPeriod=10&EndRange=55800&GameID={game_id}&RangeType=2&Season=20{year-1}-{year}&SeasonType={season_type}&StartPeriod=1&StartRange={start_range}'
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36', 'x-nba-stats-origin': 'stats', 'x-nba-stats-token': 'true', 'Host':'stats.nba.com', 'Referer':f'https://stats.nba.com/game/{game_id}/'}
            x = Game(game_id=game_id,pbp_url=pbp_url,box_url=box_url,headers=headers)
            x.compute_lineups()
            print(f'{game_id} is done')
            x.pbp.to_csv(f'pbp/pbp_raw/{game_id}_pbp.csv')
        except:
            failed.append(game_id)
            print(game_id+'failed')
failed_ids = pd.DataFrame(failed)
failed_ids.to_csv('failed_ids.csv',index=False)