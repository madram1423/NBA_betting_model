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
    made_last_ft_pattern = r'(?:1 of 1|2 of 2|3 of 3).*PTS'
    visitor_poss_filter = (
    ((df.rebound_type == 'DRB') & ~(df.homedescription.isna())) | # home team drb means visitor poss ends
    ((df.eventmsgtype == 4) & ~(df.eventmsgactiontype==1) & (~df.homedescription.isna())) | # team rebound
    (df.homedescription.str.contains('STEAL',na=False)) | # home team steal means visitor poss ends
    ((df.eventmsgtype==1) & ~(df.visitordescription.isna())) | # visitor team makes shot means visitor poss ends
    ((df.eventmsgtype==3) & df.visitordescription.str.contains(made_last_ft_pattern)) | #visitor team MAKES last ft means poss ends
    ((df.eventmsgtype == 5) & (df.homedescription.isna())) #unforced visitor turnover
    ) 
    home_poss_filter = (
    ((df.rebound_type == 'DRB') & ~(df.visitordescription.isna())) | # home team drb means visitor poss ends
    ((df.eventmsgtype == 4) & ~(df.eventmsgactiontype==1) & (~df.visitordescription.isna())) |
    (df.visitordescription.str.contains('STEAL',na=False)) |
    ((df.eventmsgtype==1) & ~(df.homedescription.isna())) |
    ((df.eventmsgtype==3) & df.homedescription.str.contains(made_last_ft_pattern)) |
    ((df.eventmsgtype == 5) & (df.visitordescription.isna()))
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

    #results += get_time_credit_list(df)
    results = results.groupby(['game_id','home_poss','away_poss','player_id','player_name','h_lineup','a_lineup']).sum().reset_index()
    return results

game_ids = ['0022300142','0022300143']
raw_pbp_paths = glob(f'.\\pbp/pbp_raw/*')
for file in raw_pbp_paths:
    df = get_raw_pbp(file)
    game_id = df['game_id'].iloc[0]
    print(game_id)
    df = get_rebound_type(df)
    df = get_possession_counts(df)
    results = aggregate_stats(df)
    df.to_csv(f'pbp/parsed_pbp/transformed_{game_id}.csv')
    results.to_csv(f'pbp/pbp_events/pbp_events_{game_id}.csv')
