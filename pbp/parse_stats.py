import pandas as pd
import numpy as np
from glob import glob
import os

def get_raw_pbp(file_path) -> pd.DataFrame:
    '''reads the raw_pbp file into a dataframe'''
    df = pd.read_csv(file_path,index_col=0,dtype={'game_id':str})

    def str_to_tuple(s):
        return tuple(s.strip('() ').replace(' ', '').split(','))

    df['h_lineup'] = df.h_lineup.apply(lambda x: str_to_tuple(x))
    df['a_lineup'] = df.a_lineup.apply(lambda x: str_to_tuple(x))
    df = df.loc[(~df.homedescription.str.contains('SUB',na=False)) & (~df.visitordescription.str.contains('SUB',na=False))].reset_index(drop=True)
    df = df.sort_values(by=['period','total_elapsed_time'])
    return df

def get_rebound_type(df) -> pd.DataFrame:
    '''Add a new column rebound_type to track whether rebounds are offensive or defensive'''
    home_rebound = (df['eventmsgtype'] ==4 ) & (~df['homedescription'].isna())
    away_rebound = (df['eventmsgtype'] ==4 ) & (~df['visitordescription'].isna())

    df.loc[df['homedescription'].str.contains('MISS',na=False),'last_missed_shot_team'] = 'home'
    df.loc[df['visitordescription'].str.contains('MISS',na=False),'last_missed_shot_team'] = 'away'

    df['last_missed_shot_team'] = df['last_missed_shot_team'].ffill()

    df.loc[home_rebound, 'rebound_type'] = df.loc[home_rebound, 'last_missed_shot_team'].apply(lambda x: 'ORB' if x == 'home' else 'DRB')
    df.loc[away_rebound, 'rebound_type'] = df.loc[away_rebound, 'last_missed_shot_team'].apply(lambda x: 'ORB' if x == 'away' else 'DRB')
    return df


def get_possession_counts(df) -> pd.DataFrame:
    '''Add column for home_poss, away_poss, has_ball'''
    made_last_ft_pattern = r'(?:1 of 1|2 of 2|3 of 3).*PTS'
    visitor_poss_filter = (
    ((df.rebound_type == 'DRB') & ~(df.homedescription.isna())) | # home team drb means visitor poss ends
    (df.homedescription.str.contains('STEAL',na=False)) | # home team steal means visitor poss ends
    ((df.eventmsgtype==1) & ~(df.visitordescription.isna())) | # visitor team makes shot means visitor poss ends
    ((df.eventmsgtype==3) & df.visitordescription.str.contains(made_last_ft_pattern)) | #visitor team MAKES last ft means poss ends
    ((df.eventmsgtype == 5) & (df.homedescription.isna())) #unforced visitor turnover

    ) 
    home_poss_filter = (
    ((df.rebound_type == 'DRB') & ~(df.visitordescription.isna())) | # home team drb means visitor poss ends
    (df.visitordescription.str.contains('STEAL',na=False)) |
    ((df.eventmsgtype==1) & ~(df.homedescription.isna())) |
    ((df.eventmsgtype==3) & df.homedescription.str.contains(made_last_ft_pattern)) |
    ((df.eventmsgtype == 5) & (df.visitordescription.isna()))
    ) 

    df['home_poss'],df['away_poss'] = 0,0
    df.loc[visitor_poss_filter,'away_poss'] = 1
    df.loc[home_poss_filter,'home_poss'] = 1

    def determine_possession(row):
        if row['home_poss'] == 1:
            return 'home'
        elif row['away_poss'] == 1:
            return 'away'
        

    df['has_ball'] = df.apply(determine_possession, axis=1)
    last_value = df['has_ball'].dropna().iloc[-1]
    df.loc[df.index[-1], 'has_ball'] = last_value
    df.loc[df.index[-2:], f'{last_value}_poss'] = 1

    df['has_ball'] = df['has_ball'].fillna(method='bfill')

    #df['has_ball'] = df['has_ball'].fillna(method='ffill')
    df.loc[df.eventmsgtype==13,'has_ball'] = 'end'

    #checks has_ball for current possession. If it's different than the last possession, that means possession changed, increment poss counter by one. 
    home_mask = df['has_ball'] == 'home'
    home_counter = df.loc[home_mask & df['has_ball'].shift(-1).isin([ 'away','end']), 'home_poss'].cumsum()
    new_index = range(df.index.min(), df.index.max() + 1)
    home_counter = home_counter.reindex(new_index, fill_value=np.NaN).fillna(method='bfill')
    df.loc[home_mask, 'home_poss'] = home_counter

    away_mask = df['has_ball'] == 'away'
    away_counter = df.loc[away_mask & df['has_ball'].shift(-1).isin([ 'home','end']) , 'away_poss'].cumsum()
    new_index = range(df.index.min(), df.index.max() + 1)
    away_counter = away_counter.reindex(new_index, fill_value=np.NaN).fillna(method='bfill')
    df.loc[away_mask, 'away_poss'] = away_counter
    return df

def get_time_credit(df) -> pd.DataFrame:
    '''add time per possession by player for all possessions they are on the court'''
    df = df.loc[(~df.homedescription.str.contains('SUB',na=False)) & (~df.visitordescription.str.contains('SUB',na=False))]
    game_id = df.game_id[0]
    box_score = pd.read_csv(f"pbp/box_scores/box_{game_id}.csv", index_col=0)
    box = box_score[["player_id", "player_name"]].values.tolist()
    id_to_name = {id: name for id, name in box}
    play_times = df.groupby(['game_id','home_poss','away_poss','h_lineup','a_lineup'])["play_elapsed_time"].sum().reset_index()
    play_times['play_end_time'] = df.groupby(['game_id','home_poss','away_poss','h_lineup','a_lineup'])["total_elapsed_time"].max().reset_index()['total_elapsed_time']
    h_expl = play_times.explode('h_lineup').reset_index(drop=True)
    h_expl.rename(columns={'h_lineup':'player_id'},inplace=True)

    a_expl = play_times.explode('a_lineup').reset_index(drop=True)
    a_expl.rename(columns={'a_lineup':'player_id'},inplace=True)

    h_expl = h_expl.merge(play_times,on= ['game_id','home_poss','away_poss','a_lineup','play_elapsed_time','play_end_time'])
    a_expl = a_expl.merge(play_times,on= ['game_id','home_poss','away_poss','h_lineup','play_elapsed_time','play_end_time'])
    time_credits = pd.concat((h_expl,a_expl))
    time_credits['player_name'] = time_credits['player_id'].apply(lambda x: id_to_name[int(x)])
    time_credits['player_id'] = time_credits['player_id'].astype(int)
    return time_credits

def aggregate_stats(df) -> pd.DataFrame:
    '''using stat filters to aggregate all the stats for the game and the play that they occurred on'''
    def get_stat_df(pbp_df,filter,stat_type,stat_value,player_num='1'):
        filtered_df = pbp_df.loc[filter][['game_id','eventnum',f'player{player_num}_id',f'player{player_num}_name','h_lineup','a_lineup','home_poss','away_poss']]
        filtered_df.rename(columns={f'player{player_num}_id': 'player_id',
                            f'player{player_num}_name': 'player_name'},inplace=True )
        filtered_df[stat_type] = stat_value
        return filtered_df

    fga_filter = (df.eventmsgtype==1) | (df.eventmsgtype==2)
    two_pt_filter = (df.eventmsgtype==1) & ~((df.homedescription.str.contains('3PT',na=False)) | (df.visitordescription.str.contains('3PT',na=False)))
    three_pt_filter = (df.eventmsgtype==1) & ((df.homedescription.str.contains('3PT',na=False)) | (df.visitordescription.str.contains('3PT',na=False)))
    three_a_filter = ((df.homedescription.str.contains('3PT',na=False)) | (df.visitordescription.str.contains('3PT',na=False)))
    ft_filter = (df.eventmsgtype==3) & ((df.homedescription.str.contains('PTS',na=False)) | (df.visitordescription.str.contains('PTS',na=False)))
    fta_filter = df.eventmsgtype==3 
    assist_filter = (df.eventmsgtype==1) & ~df.player2_name.isnull()
    orb_filter = df.rebound_type == 'ORB'
    drb_filter = df.rebound_type == 'DRB'
    trb_filter = orb_filter | drb_filter
    stl_filter = df.homedescription.str.contains('STEAL',na=False) | df.visitordescription.str.contains('STEAL',na=False)
    blk_filter = df.homedescription.str.contains('BLOCK',na=False) | df.visitordescription.str.contains('BLOCK',na=False)
    to_filter = df.eventmsgtype==5
    foul_filter = df.eventmsgtype==6
    #results is a dataframe of every stat credit for every play
    results = get_stat_df(df,two_pt_filter,'PTS',2)
    results =pd.concat((results, get_stat_df(df,three_pt_filter,'PTS',3)))
    results =pd.concat((results, get_stat_df(df,ft_filter,'PTS',1)))

    results =pd.concat((results, get_stat_df(df,two_pt_filter,'FGM',1)))
    results =pd.concat((results, get_stat_df(df,three_pt_filter,'3PM',1)))
    results =pd.concat((results, get_stat_df(df,three_pt_filter,'FGM',1)))
    results =pd.concat((results, get_stat_df(df,ft_filter,'FTM',1)))

    results =pd.concat((results, get_stat_df(df,fga_filter,'FGA',1)))
    results =pd.concat((results, get_stat_df(df,fta_filter,'FTA',1)))
    results =pd.concat((results, get_stat_df(df,three_a_filter,'3PA',1)))

    results =pd.concat((results, get_stat_df(df,trb_filter,'TRB',1)))
    results =pd.concat((results, get_stat_df(df,drb_filter,'DRB',1)))
    results =pd.concat((results, get_stat_df(df,orb_filter,'ORB',1)))

    results =pd.concat((results, get_stat_df(df,stl_filter,'STL',1,player_num=2)))
    results =pd.concat((results, get_stat_df(df,blk_filter,'BLK',1,player_num=3)))
    results =pd.concat((results, get_stat_df(df,to_filter,'TOV',1,player_num=1)))
    results =pd.concat((results, get_stat_df(df,foul_filter,'PF',1)))

    results =pd.concat((results, get_stat_df(df,assist_filter,'AST',1,player_num='2')))
    time_credits = get_time_credit(df)
    results = pd.concat((results,time_credits))
    #grouping all the stats earned by the play they occurred on
    results = results.groupby(['game_id','home_poss','away_poss','player_id','player_name','h_lineup','a_lineup']).sum().reset_index()
    return results

def get_team_names(results,game_id) -> pd.DataFrame:
    '''getting team names for each player and adding them to the resulting dataframe
       need to read from the box score because some players don't record any stats'''
    box = pd.read_csv(f"pbp/box_scores/box_{game_id}.csv", index_col=0)
    away_team_name = box['team_abbreviation'].iloc[0]
    home_team_name = box['team_abbreviation'].iloc[-1]
    opp_team_dict = {away_team_name:home_team_name,
                    home_team_name:away_team_name}
    team_to_id_list = box[['team_abbreviation','player_id']].values
    player_team_dict = {player_id:team for (team,player_id) in team_to_id_list}
    results['team'] = results['player_id'].apply(lambda x: player_team_dict.get(x,0))
    results['opp'] = results['team'].apply(lambda x: opp_team_dict.get(x,'N/A'))
    results['H/A'] = results['team'].apply(lambda x: 1 if x == home_team_name else 0)
    return results

def add_off_def_poss(results) -> pd.DataFrame:
    '''using the H/A column and the home_poss def_poss columns to determine if this player is on offense or defense'''
    results['off_poss'] = np.NaN
    results['def_poss'] = np.NaN
    results.loc[((results['H/A']==1) & (results.home_poss != 0)), 'off_poss'] = results['home_poss']  # player is on home team, home team has ball, therefore offensive
    results.loc[((results['H/A']==0) & (results.away_poss != 0)), 'off_poss'] = results['away_poss']  # player is on visitor team, visitor team has ball, therefore offensive

    results.loc[((results['H/A']==1) & (results.away_poss != 0)), 'def_poss'] = results['away_poss']  #player is on home team, away team has ball, therefore defensive
    results.loc[((results['H/A']==0) & (results.home_poss != 0)), 'def_poss'] = results['home_poss']  #player is on away team, home team has ball, therefore defensive
    results['off_poss'].fillna(0,inplace=True)
    results['def_poss'].fillna(0,inplace=True)
    results = results[['game_id','player_id', 'player_name', 'play_elapsed_time','play_end_time', 'team', 'opp', 'H/A', 'off_poss', 'def_poss',
        'h_lineup', 'a_lineup', 'FGM', '3PM', 'FTM', 'FGA',
        'FTA', '3PA', 'TRB', 'DRB', 'ORB', 'STL', 'BLK', 'TOV', 'PF', 'AST','PTS'
        ]]#dropping eventnum, home_poss,away_poss as well as reordering
    return results

def compare_to_box(results,game_id):
    stats = ['PTS','TRB','AST','BLK','STL','DRB','ORB','FGM','FGA','3PM','3PA','FTA','FTM']
    box = pd.read_csv(f"pbp/box_scores/box_{game_id}.csv", index_col=0,dtype={'game_id':str})
    box = box.loc[~box['min'].isna()]
    box_from_results = results.groupby(['game_id','player_id','player_name','team','opp'])[stats].sum().reset_index()
    box.columns = ['game_id', 'team_id', 'team_abbreviation', 'team_city', 'player_id',
       'player_name', 'nickname', 'start_position', 'comment', 'min', 'FGM',
       'FGA', 'fg_pct', '3PM', '3PA', 'fg3_pct', 'FTM', 'FTA', 'ft_pct',
       'ORB', 'DRB', 'TRB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS',
       'plus_minus']
    compare = box_from_results.merge(box)
    #print(box_from_results.loc[box_from_results.player_name==player][stats])
    #print(box.loc[box.player_name==player][stats])
    wrong = list(set(box.player_name.values) - set(compare.player_name.values))
    return len(wrong)
    return 

def prod():
    for n in range(len(game_ids)):  #range(len(game_ids)):
        game_id = game_ids.loc[n,'game_id']
        raw_pbp_path = f'pbp/pbp_raw/{game_id}_pbp.csv'
        event_path = f'pbp/pbp_events/pbp_events_{game_id}.csv'
        if not os.path.isfile(event_path):
            print(game_id,'Processing')
            df = get_raw_pbp(raw_pbp_path)
            game_id = df['game_id'].iloc[0]
            df = get_rebound_type(df)
            df = get_possession_counts(df)
            results = aggregate_stats(df)
            results = get_team_names(results,game_id)
            test = compare_to_box(results,game_id)
            if test > 0:
                print(game_id,test)
            df.to_csv(f'pbp/parsed_pbp/transformed_{game_id}.csv')
            results.to_csv(f'pbp/pbp_events/pbp_events_{game_id}.csv')
        else:
            print(f'{game_id} already processed')
    return

def test_game_id(game_id):
    raw_pbp_path = f'pbp/pbp_raw/{game_id}_pbp.csv'
    print(game_id,'Processing')
    df = get_raw_pbp(raw_pbp_path)
    df = get_rebound_type(df)
    df = get_possession_counts(df)
    results = aggregate_stats(df)
    results = get_team_names(results,game_id)
    results = add_off_def_poss(results)
    compare_to_box(results,game_id)
    transformed_path = f'pbp/parsed_pbp/transformed_{game_id}'
    df.to_csv(f'pbp/parsed_pbp/transformed_{game_id}.csv')
    results.to_csv(f'pbp/pbp_events/pbp_events_{game_id}.csv')
    #os.system(f"start EXCEL.EXE {transformed_path}")
    return

game_ids = pd.read_csv('pbp/game_ids.csv',dtype={'game_id':'str'})
prod()
#test_game_id('0022200004')