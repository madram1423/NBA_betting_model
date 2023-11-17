import pandas as pd
import datetime as dt
import re
from unidecode import unidecode
from betting_functions import get_url_json

dog_props_url = 'https://api.underdogfantasy.com/beta/v3/over_under_lines'
data = get_url_json(dog_props_url)

df = pd.json_normalize(list(data.values()))
df.index = data.keys()
new = df.T['over_under_lines'].values
lines = pd.json_normalize(new)

test =  pd.json_normalize(df.T['players'])
player_df = test.copy(deep=True)
player_df = player_df[['id','first_name', 'last_name',
       'sport_id','team_id']]
player_df = player_df.dropna()#

player_df.loc[player_df.sport_id=='ESPORTS']
x = player_df[player_df.sport_id=='ESPORTS']
p2esport = x[['last_name','first_name']].to_dict('split')
p2esport = dict(p2esport['data'])

test =  pd.json_normalize(df.T['players'])
player_df = test.copy(deep=True)
player_df = player_df[['id','first_name', 'last_name',
       'sport_id','team_id']]
player_df = player_df.dropna()
player_df.loc[player_df['sport_id'] != 'ESPORTS', 'full_name'] = player_df['first_name']+' ' + player_df['last_name']
player_df.loc[player_df['sport_id'] == 'ESPORTS', 'full_name'] = player_df['last_name']
#player_df['full_name'] = player_df['first_name']+' ' + player_df['last_name']
player_df = player_df[['full_name','sport_id','team_id']]
p2l = player_df[['full_name','sport_id']].to_dict('split')
p2tm = player_df[['full_name','team_id']].to_dict('split')
temp = p2l['data']
temp2 = p2tm['data']
p2l = dict(temp)
p2tm = dict(temp2)

first2 = player_df['full_name'].apply(lambda x: ' '.join(x.split()[0:2]))
names = pd.DataFrame((first2,player_df.full_name))
names = names.T
names.columns=['first2','fullname']
names.loc[names.first2=='Jazz Chisholm']
first2full = names.to_dict('split')
first2full = dict(first2full['data'])

games = pd.json_normalize(df.T['games'].values).dropna(how='all')

def to_central(date_str):
    x = pd.to_datetime(date_str)
    x = x.tz_convert('US/Central')
    return str(x.date())

games.scheduled_at = games.scheduled_at.apply(to_central)

#grabbing team names from match title
matchup = games['title']
home = []
away = []
for i in matchup:
    temp = re.split(' @ |, |vs.',i)
    home.append(temp[0])
    away.append(temp[1])
#fixing esports team names
for i in range(len(home)):
    home[i] = home[i].split(': ')[-1]
    
for i in range(len(away)):
    away[i] = away[i].split(': ')[-1]

matchup = pd.DataFrame((away,home,games.away_team_id,games.home_team_id)).T
matchup.columns = ['Home', 'Away','away_id','home_id']
dates = games['scheduled_at'].values
#temp = []
#for i in dates:
#    temp.append(i.split('T')[0])
matchup['Date'] = dates
id2tm =  matchup[['home_id','Home']].to_dict('split')
id2tmaway =  matchup[['away_id','Away']].to_dict('split')
id2tm = dict(id2tm['data'])
id2tmaway = dict(id2tmaway['data'])
id2tm.update(id2tmaway)

lines = lines[['stat_value','over_under.appearance_stat.stat', 'over_under.title']]
lines
players = lines['over_under.title'].values
guys = []
for i in players:
    temp = i.split()
    final = temp[0] + ' '+temp[1]
    guys.append(final)
    
guys
lines= lines.rename(columns={'stat_value':'Line','over_under.appearance_stat.stat':'Stat', 'over_under.title':'title'})
lines['Player']= guys
lines['Player'] = lines['Player'].apply(lambda x: unidecode(x).replace('_',' '))

def map_name(x):
    if x is None:
        return None
    if x in first2full:
        return first2full[x]
    elif x.split(': ')[-1] in first2full:
        return x.split(': ')[-1]
    elif x.split()[-1] in first2full:
        return x.split()[-1]
    else:
        return x

lines['Player'] = lines['Player'].apply(lambda x: map_name(x))

league = []
team_id = []
for p in guys:
    if p in p2l:
        league.append(p2l[p])
        team_id.append(p2tm[p])
    elif p.split()[-1] in p2l:
        league.append(p2l[p.split()[-1]])
        team_id.append(p2tm[p.split()[-1]])
    else:
        league.append('other')
        team_id.append('other')
lines['League'] = league

def map_team(x):
    if x in p2tm:
        return p2tm[x]
    elif p.split()[-1] in p2l:
        return p2tm[p.split()[-1]]
    else:
        return x

lines['team_id'] = lines.Player.apply(lambda x: map_team(x))

def map_id(x):
    if x in id2tm:
        return id2tm[x]
    else:
        return x
    
final = pd.merge(lines,matchup, how='left',left_on='team_id',right_on='away_id')
final = final.drop(['Home', 'Away','home_id','away_id'], axis=1)
final2 = pd.merge(final,matchup, how='left',left_on='team_id',right_on='home_id')
final2 = final2.drop(['Home', 'Away','home_id','away_id'], axis=1)
final2['Date'] = final2['Date_x'].fillna(final2['Date_y'])
final2 = final2.drop(['Date_x', 'Date_y'], axis=1)
final2['team_id'] = final2.team_id.apply(lambda x: map_id(x))
final2.columns = ['Line', 'Stat', 'title', 'Player', 'League', 'Team', 'Date']
df = final2[['Line', 'Stat', 'Player', 'League', 'Team', 'Date']].copy(deep=True)
df = df.reset_index(drop=True)
syntax = {
    'pts_rebs_asts': 'PTS+TRB+AST',
    'pts_rebs': 'PTS+TRB',
    'points': 'PTS',
    'free_throws_made': 'FT',
    'fantasy_points': 'Fantasy',
    'rebounds': 'TRB',
    'assists': 'AST',
    'steals': 'STL',
    'blocks': 'BLK',
    'blks_stls': 'BLK+STL',
    'turnovers': 'TO',
    'rebs_asts': 'TRB+AST',
    'pts_asts': 'PTS+AST',
    'three_points_made': '3PM',
    'shots': 'Shots',
    'goals': 'Goals',
    'saves': 'Goalie Saves',
    'clearances': 'Clearances',
    'goals_and_assists': 'Goals and Assists',
    'tackles': 'Tackles',
    'interceptions': 'Interceptions',
    'crosses': 'Crosses',
    'goals_against': 'Goal Against',
    'game_1_and_2_kills': 'MAPS 1-2 Kills',
    'map_1_and_2_kills': 'MAPS 1-2 Kills',
    'kills_in_maps_1_2': 'MAPS 1-2 Kills',
    'Headshots on Maps 1+2': 'MAPS 1-2 Headshots',
    'strokes': 'Strokes',
    'bogeys_or_worse': 'Bogeys or Worse',
    'birdies_or_better': 'Birdies or Better',
    'aces': 'Aces',
    'breakpoints_won': 'Break Points Won',
    'games_won': 'Games Won',
    'games_lost': 'Games Lost',
    'total_games': 'Total Games',
    'double_faults': 'Double Faults',
    'service_games_lost': 'Service Games Lost',
    'Fastest Laps': 'Fastest Laps',
    'position': 'position',
    'passing_yds': 'Pass Yards',
    'rushing_yds': 'Rush Yards',
    'receiving_yds': 'Receiving Yards' ,
    'fantasy_points': 'Hitter Fantasy Score',
    'strikeouts': 'Pitcher Strikeouts',
    'hits_runs_rbis': 'PTS',
    'singles':'Singles',
    'total_bases': 'Total Bases',
    'walks': 'Walks Allowed',
    'hits': 'Hits Allowed',
    'kills_in_map_1' : 'MAPS 1 Kills',
    'kills_in_maps_1_2_3' : 'MAPS 1-3 Kills',
    'kills_in_map_1': 'MAP 1 Kills',
    'kills_in_map_2': 'MAP 2 Kills',
    'kills_in_map_3': 'MAP 3 Kills',
    'fantasy_points_on_maps_1_2_3': 'MAPS 1-3 Fantasy points',
    'fantasy_points_on_map_1': 'MAP 1 Fantasy points',
    'fantasy_points_on_map_2': 'MAP 2 Fantasy points',
    'fantasy_points_on_map_3': 'MAP 3 Fantasy points',
    'deaths_on_maps_1_2_3' : 'MAP 1-3 Deaths',
    'deaths_in_map_2' : 'MAP 2 Deaths',
    'deaths_in_map_3' : 'MAP 3 Deaths',
    'field_goals_att': 'FGA',
    'three_points_att': '3PA',
    'personal_fouls': 'PF',
    'passing_att': 'Pass Attempts',
    'passing_comps': 'Pass Completions',
    'passing_ints': 'Pass Interceptions',
    'passing_and_rushing_yds': 'Pass and Rush Yards',
    'rushing_att': 'Rush Attempts',
    'rush_rec_yds': 'Rush+Rec Yards',
    'receiving_rec': 'Receptions',
    'field_goals_made': 'FGM',
    'kicking_points': 'Kicking Points',
    'tackles_and_assists': 'Tackles+Ast',
    'passing_tds': 'Pass TD',
    'rush_rec_tds': 'Rush+Rec Touchdowns',
    'extra_points_made': 'XP',
    'blocked_shots': 'BLK',
    'shots_attempted': 'Shots',
    'goals_assists': 'Goals and Assists',
    'shots_on_target': 'Shots on Target',
    'fouls_against': 'Fouls Against',
    'assists_on_map_1': 'MAP 1 Assists',
    'assists_in_map_2': 'MAP 2 Assists',
    'fantasy_points_in_map_3': 'MAP 3 Fantasy Points',
    'assists_on_maps_1_2_3': 'MAP 1-3 Assists',
    'assists_in_map_3': 'MAP 3 Assists',
    'kills_on_maps_1_2_3': 'MAP 1-3 Kills',
    'deaths_on_map_1': 'MAP 1 Deaths',
    'headshots_on_maps_1_2': 'MAP 1-2 Headshots',
    'significant_strikes': 'Significant Strikes',
    'fight_time': 'Fight Time',
    'total_yds': 'Total Yards',
    'games_played': 'GP',
                }

df = df.replace(syntax)

today = dt.date.today()
df.columns = [x.lower() for x in df.columns]
df.to_csv(f'Lines/dog/doglines_{today.month}_{today.day}.csv')
print('underdog scrape successful')