import datetime as dt
import json
import os

import numpy as np
import pandas as pd
import requests

box_url = 'https://stats.nba.com/stats/boxscoretraditionalv2?EndPeriod=10&EndRange=28800&GameID=0041800237&RangeType=0&Season=2018-19&SeasonType=Playoffs&StartPeriod=1&StartRange=0'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64)', 'x-nba-stats-origin': 'stats', 'x-nba-stats-token': 'true', 'Host':'stats.nba.com', 'Referer':'https://stats.nba.com/game/0021900306/'}
r= requests.get(box_url, headers=headers, timeout = 7)
data = json.loads(r.text)
box = pd.DataFrame.from_dict(data['resultSets'][0]['rowSet'])
col_names = data['resultSets'][0]['headers']
box.columns = col_names
box.columns = box.columns.str.lower()

pbp_url = 'https://stats.nba.com/stats/playbyplayv2?EndPeriod=10&EndRange=55800&GameID=0041800237&RangeType=2&Season=2018-19&SeasonType=Playoffs&StartPeriod=1&StartRange=0'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64)', 'x-nba-stats-origin': 'stats', 'x-nba-stats-token': 'true', 'Host':'stats.nba.com', 'Referer':'https://stats.nba.com/game/0021900306/'}
r= requests.get(pbp_url, headers=headers, timeout = 5)
data = json.loads(r.text)
pbp = pd.DataFrame.from_dict(data['resultSets'][0]['rowSet'])
col_names = data['resultSets'][0]['headers']
pbp.columns = col_names
pbp.columns = pbp.columns.str.lower()
pbp_times = pbp['pctimestring'].str.split(':',2, expand=True)
pbp_times[0] = pbp_times[0].astype(str).astype(int)
pbp_times[1] = pbp_times[1].astype(str).astype(int)
pbp['timeinseconds'] = (pbp_times[0]*60) + pbp_times[1]
pbp['play_elapsed_time'] = pbp['timeinseconds'].shift(1)  - pbp['timeinseconds'] 
pbp['play_elapsed_time'] = pbp['play_elapsed_time'].fillna(0)
pbp['play_elapsed_time'] = np.where(pbp['period'] != pbp['period'].shift(1), 0, pbp['play_elapsed_time'])
pbp['total_elapsed_time'] = pbp.groupby(['game_id'])['play_elapsed_time'].cumsum()
pbp['max_time'] = pbp.groupby('game_id')['play_elapsed_time'].transform('sum')
pbp['time_remaining'] = pbp['max_time'] - pbp['total_elapsed_time']
pbp['scoremargin'] = np.where(pbp['scoremargin']=='TIE',0,pbp['scoremargin'])
pbp['scoremargin'] = pbp['scoremargin'].fillna(0).astype(int)


def getQuarterStarters(quarter):
    if quarter == 1:
        start_range = 0
        end_range = 50
    elif quarter == 2:
        start_range = 7201
        end_range = 7493
    elif quarter == 3:
        start_range = 14410
        end_range = 14640
    elif quarter == 4:
        start_range = 21621
        end_range = 21913
        
    starters_url = 'https://stats.nba.com/stats/boxscoretraditionalv2?EndPeriod=14&GameID=0041800237&RangeType=2&Season=2018-19&SeasonType=Playoffs&StartPeriod=1&StartRange=' + str(start_range) + '&EndRange=' + str(end_range)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64)', 'x-nba-stats-origin': 'stats', 'x-nba-stats-token': 'true', 'Host':'stats.nba.com', 'Referer':'https://stats.nba.com/game/0021900306/'}
    r= requests.get(starters_url, headers=headers, timeout = 5)
    data = json.loads(r.text)
    starters = pd.DataFrame.from_dict(data['resultSets'][0]['rowSet'])
    col_names = data['resultSets'][0]['headers']
    starters.columns = col_names
    starters.columns = starters.columns.str.lower()
    return starters[['game_id', 'team_id', 'team_abbreviation', 'player_id',
       'player_name']]



class Game():
    def __init__(self,pbp,box):
        self.pbp = pbp
        self.box = box
        self.hteam = self.box.team_abbreviation.unique()[1]
        self.ateam = self.box.team_abbreviation.unique()[0]
        self.pbp['h_lineup'] = ''
        self.pbp['a_lineup'] = ''
        
        
    def parse_game(self):
        #getting starters from boxscore df
        print('home',self.hteam)
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
        for idx, row in pbp2.iterrows():
            if row.pctimestring == '12:00' and row.period != 1:
                qstart = getQuarterStarters(row.period)
                qstarth = qstart.loc[qstart.team_abbreviation == self.hteam]
                qstarta = qstart.loc[qstart.team_abbreviation != self.hteam]
                self.pbp.at[idx,'h_lineup'] = sorted(qstarth.player_id.to_list())
                self.pbp.at[idx,'a_lineup'] = sorted(qstarta.player_id.to_list())
        
        prev_h_lineup = self.h_starters.copy()  # Initialize with the starting lineup
        prev_a_lineup = self.a_starters.copy()  # Initialize with the starting lineup

        for idx, row in self.pbp.iterrows():
            if row.pctimestring == '12:00':
                h_lineup = sorted(row['h_lineup'])  # Use the existing lineup for the beginning of the quarter
                a_lineup = sorted(row['a_lineup'])  # Use the existing lineup for the beginning of the quarter
            else:
                h_lineup = prev_h_lineup.copy()  # Create a copy of the previous h_lineup
                a_lineup = prev_a_lineup.copy()  # Create a copy of the previous a_lineup

                if isinstance(row['homedescription'], str) and row['homedescription'].startswith('SUB'):
                    h_lineup.remove(row['player1_id'])
                    h_lineup.append(row['player2_id'])

                if isinstance(row['visitordescription'], str) and row['visitordescription'].startswith('SUB'):
                    a_lineup.remove(row['player1_id'])
                    a_lineup.append(row['player2_id'])

            self.pbp.at[idx, 'h_lineup'] = sorted(h_lineup)
            self.pbp.at[idx, 'a_lineup'] = sorted(a_lineup)
            prev_h_lineup = h_lineup  # Update the previous h_lineup for the next iteration
            prev_a_lineup = a_lineup  # Update the previous a_lineup for the next iteration
        self.pbp['a_lineup'] = self.pbp['a_lineup'].apply(lambda x: tuple(x))
        self.pbp['h_lineup'] = self.pbp['h_lineup'].apply(lambda x: tuple(x))
        return 



        
    
    
x = Game(pbp,box)
x.parse_game()
#x.get_stats()