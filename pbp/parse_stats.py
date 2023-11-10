import pandas as pd
import numpy as np
from glob import glob

def get_raw_pbp(file_path) -> pd.DataFrame:
    df = pd.read_csv(file_path,index_col=0,dtype={'game_id':str})

    def str_to_tuple(s):
        return tuple(s.strip('() ').replace(' ', '').split(','))

    df['h_lineup'] = df.h_lineup.apply(lambda x: str_to_tuple(x))
    df['a_lineup'] = df.a_lineup.apply(lambda x: str_to_tuple(x))
    return df

def get_rebound_type(df) -> pd.DataFrame:
    #allll this ugly stuff just to get a column called 'rebound_type'
    mask = (df.eventmsgtype == 4) & (~df.homedescription.isnull() | ~df.visitordescription.isnull())
    pattern = r'Off:(\d+) Def:(\d+)'

    home_extract = df['homedescription'].str.extract(pattern)
    df['offensive_rebounds'] = home_extract[0]
    df['defensive_rebounds'] = home_extract[1]

    visitor_extract = df['visitordescription'].str.extract(pattern)
    df['offensive_rebounds'].fillna(visitor_extract[0], inplace=True)
    df['defensive_rebounds'].fillna(visitor_extract[1], inplace=True)

    df[['offensive_rebounds', 'defensive_rebounds']] = df[['offensive_rebounds', 'defensive_rebounds']].fillna(0)
    df[['offensive_rebounds', 'defensive_rebounds']] = df[['offensive_rebounds', 'defensive_rebounds']].astype(int)
    df['def_reb_previous'] = df[mask].groupby('player1_id')['defensive_rebounds'].shift(fill_value=0)
    df['off_reb_previous'] = df[mask].groupby('player1_id')['offensive_rebounds'].shift(fill_value=0)
    df.sort_values(by=['period','total_elapsed_time','eventnum'],inplace=True)
    df['rebound_type'] = ''
    df.loc[(df.defensive_rebounds > df.def_reb_previous), 'rebound_type'] = 'DRB'
    df.loc[(df.offensive_rebounds > df.off_reb_previous), 'rebound_type'] = 'ORB'
    df.drop([ 'offensive_rebounds', 'defensive_rebounds', 'def_reb_previous', 'off_reb_previous'],inplace=True,axis=1)
    df.sort_values(by=['period','total_elapsed_time','eventnum'],inplace=True)
    return df



def get_possession_counts(df) -> pd.DataFrame:
    missed_last_home_shot = (df['eventmsgtype'].shift() == 2) & (~df['homedescription'].shift().isna())
    missed_last_away_shot = (df['eventmsgtype'].shift() == 2) & (~df['homedescription'].shift().isna())
    home_rebound = (df['eventmsgtype'] ==4 ) & (~df['homedescription'].isna())
    away_rebound = (df['eventmsgtype'] ==4 ) & (~df['homedescription'].isna())


    made_last_ft_pattern = r'(?:1 of 1|2 of 2|3 of 3).*PTS'
    visitor_poss_filter = (
    ((df.rebound_type == 'DRB') & ~(df.homedescription.isna())) | # home team drb means visitor poss ends
    ((df.eventmsgtype == 4) & (df.player1_name.isna()) & (df.visitordescription.isna())) | # team rebound
    (df.homedescription.str.contains('STEAL',na=False)) | # home team steal means visitor poss ends
    ((df.eventmsgtype==1) & ~(df.visitordescription.isna())) | # visitor team makes shot means visitor poss ends
    ((df.eventmsgtype==3) & df.visitordescription.str.contains(made_last_ft_pattern)) | #visitor team MAKES last ft means poss ends
    ((df.eventmsgtype == 5) & (df.homedescription.isna())) |#unforced visitor turnover
    (home_rebound & missed_last_away_shot)
    ) 
    home_poss_filter = (
    ((df.rebound_type == 'DRB') & ~(df.visitordescription.isna())) | # home team drb means visitor poss ends
    ((df.eventmsgtype == 4) & (df.player1_name.isna()) & (df.homedescription.isna())) |
    (df.visitordescription.str.contains('STEAL',na=False)) |
    ((df.eventmsgtype==1) & ~(df.homedescription.isna())) |
    ((df.eventmsgtype==3) & df.homedescription.str.contains(made_last_ft_pattern)) |
    ((df.eventmsgtype == 5) & (df.visitordescription.isna()))|
    (away_rebound & missed_last_home_shot)
    ) 

    df['home_poss'],df['away_poss'] = 0,0
    df.loc[visitor_poss_filter,'away_poss'] = 1
    df.loc[home_poss_filter,'home_poss'] = 1
    # Determine the most recent possession
    def determine_possession(row):
        if row['home_poss'] == 1:
            return 'home'
        elif row['away_poss'] == 1:
            return 'away'

    df['home_poss'],df['away_poss'] = 0,0
    df.loc[visitor_poss_filter,'away_poss'] = 1
    df.loc[home_poss_filter,'home_poss'] = 1
    # Apply the function to each row to create a new 'new_col' column
    df['has_ball'] = df.apply(determine_possession, axis=1)

    # Fill NaN values in the 'new_col' column based on the previous row
    df['has_ball'] = df['has_ball'].fillna(method='bfill')

    home_mask = df['has_ball'] == 'home'
    home_counter = df.loc[home_mask & (df['has_ball'].shift(-1) == 'away'), 'home_poss'].cumsum()
    new_index = range(df.index.min(), df.index.max() + 1)
    home_counter = home_counter.reindex(new_index, fill_value=np.NaN).fillna(method='bfill')

    # Use the correct DataFrame column to assign values
    df.loc[home_mask, 'home_poss'] = home_counter

    away_mask = df['has_ball'] == 'away'
    away_counter = df.loc[away_mask & (df['has_ball'].shift(-1) == 'home'), 'away_poss'].cumsum()
    new_index = range(df.index.min(), df.index.max() + 1)
    away_counter = away_counter.reindex(new_index, fill_value=np.NaN).fillna(method='bfill')

    # Use the correct DataFrame column to assign values
    df.loc[away_mask, 'away_poss'] = away_counter
    return df

def get_time_credit(df):
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

def aggregate_stats(df):
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
    trb_filter = (df.rebound_type == 'DRB') | (df.rebound_type == 'ORB')
    stl_filter = df.homedescription.str.contains('STEAL',na=False) | df.visitordescription.str.contains('STEAL',na=False)
    blk_filter = df.homedescription.str.contains('BLOCK',na=False) | df.visitordescription.str.contains('BLOCK',na=False)
    to_filter = df.eventmsgtype==5
    foul_filter = df.eventmsgtype==6

    #results is a list of every stat credit for every play
    results = get_stat_df(df,two_pt_filter,'PTS',2)
    results =pd.concat((results, get_stat_df(df,three_pt_filter,'PTS',3)))
    results =pd.concat((results, get_stat_df(df,ft_filter,'PTS',1)))

    results =pd.concat((results, get_stat_df(df,two_pt_filter,'FGM',1)))
    results =pd.concat((results, get_stat_df(df,three_pt_filter,'3PM',1)))
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
    results = results.groupby(['game_id','home_poss','away_poss','player_id','player_name','h_lineup','a_lineup']).sum().reset_index()
    return results

def get_team_names(results,game_id):
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
    results['off_poss'] = np.NaN
    results['def_poss'] = np.NaN
    results.loc[((results['H/A']==1) & (results.home_poss != 0)), 'off_poss'] = results['home_poss']  # player is on home team, home team has ball, therefore offensive
    results.loc[((results['H/A']==0) & (results.away_poss != 0)), 'off_poss'] = results['away_poss']  # player is on visitor team, visitor team has ball, therefore offensive

    results.loc[((results['H/A']==1) & (results.away_poss != 0)), 'def_poss'] = results['away_poss']  #player is on home team, away team has ball, therefore defensive
    results.loc[((results['H/A']==0) & (results.home_poss != 0)), 'def_poss'] = results['home_poss']  #player is on away team, home team has ball, therefore defensive
    results['off_poss'].fillna(0,inplace=True)
    results['def_poss'].fillna(0,inplace=True)
    results = results[['game_id','player_id', 'player_name', 'home_poss', 'away_poss', 'play_elapsed_time','play_end_time', 'team', 'opp', 'H/A', 'off_poss', 'def_poss',
        'h_lineup', 'a_lineup', 'FGM', '3PM', 'FTM', 'FGA',
        'FTA', '3PA', 'TRB', 'DRB', 'ORB', 'STL', 'BLK', 'TOV', 'PF', 'AST','PTS'
        ]]#dropping eventnum, home_poss,away_poss as well as reordering

    return results
import os

#for file in ['pbp/pbp_raw/0022300142_pbp.csv']:

game_ids = pd.read_csv('pbp/game_ids.csv',dtype={'game_id':'str'})

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
    transformed_path = f'pbp/parsed_pbp/transformed_{game_id}'
    df.to_csv(f'pbp/parsed_pbp/transformed_{game_id}.csv')
    results.to_csv(f'pbp/pbp_events/pbp_events_{game_id}.csv')
    os.system(f"start EXCEL.EXE {transformed_path}")
    return

prod()
#test_game_id('0022200002')