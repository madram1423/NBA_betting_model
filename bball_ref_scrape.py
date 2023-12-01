import pandas as pd
import tls_client
from bs4 import BeautifulSoup
from unidecode import unidecode
from betting_functions import get_url_soup
import time

requests = tls_client.Session(
    client_identifier="chrome112",
)
#years = ['2024','2023','2022','2021','2020','2019','2018','2017','2016','2015','2014','2013','2012','2011','2010']
years = ['2024']
for year in years:
    soup = get_url_soup(f'https://www.basketball-reference.com/leagues/NBA_{year}_per_game.html')

    # Find all <td> elements with the 'data-append-csv' attribute
    td_elements = soup.find_all('td', {'data-append-csv': True})

    # Create empty lists to store the extracted data
    player_codes = []

    # Loop through the <td> elements
    for td_element in td_elements:
        data_append_csv = td_element['data-append-csv']
        player_name = td_element.find('a').text
        player_codes.append([player_name,data_append_csv])

    rows = soup.find_all('tr', class_=['full_table', 'italic_text partial_table'])

    # Create a list to store the 'pos' values
    positions = []

    # Loop through the rows and extract the 'pos' value for each row
    for row in rows:
        pos_element = row.find('td', {'data-stat': 'pos'})
        if pos_element:
            position = pos_element.text
            positions.append(position)
    print(len(player_codes),len(positions))
    code_df = pd.DataFrame(player_codes,columns=['name','code'])
    code_df['pos'] = positions
    code_df.drop_duplicates(inplace=True)
    code_df = code_df.reset_index(drop=True)
    code_df = code_df.groupby('name').first().reset_index()

    def get_headers(soup):
        i = 0
        while i < 40:
            headers = [th.getText() for th in soup.findAll('tr', limit=40)[i].findAll('th')]
            i = i +1
            if headers:
                idx = i
                i = 41
        return headers[1:]

    def get_stats_df(soup,headers,player):

        rows = soup.findAll('tr')
        player_stats = [[td.getText() for td in rows[i].findAll('td')]
                    for i in range(len(rows))]
        player_stats = [x for x in player_stats if len(x) > 4]
        stats = pd.DataFrame(player_stats, columns = headers)
        stats.insert(0, 'player', player)
        stats.index = range(len(stats))
        return stats

    def get_stats(num,df):
        for person in range(num):
            errors = []
            try:
                player_id = df['code'].iloc[person]
                player_name = df['name'].iloc[person]
                base = f'https://www.basketball-reference.com/players/c/{player_id}/gamelog/'
                url = base+year
                time.sleep(2.95)
                soup = get_url_soup(url)
                
                headers = get_headers(soup)
                stats = get_stats_df(soup,headers,player_name)
                stats['pos'] = df['pos'].iloc[person]
                stats['season'] = year
                if person == 0:
                    data_core = stats
                else:
                    data_core = pd.concat([data_core,stats])
                if person % 5 == 0:
                    print(url)
                    print(person,player_name)
            except: 
                errors.append(player_id)
        print(errors)
        return data_core

    print(len(code_df))
    data = get_stats(len(code_df),code_df)

    data['Date'] = pd.to_datetime(data['Date'])
    for i in range(len(data)):
        data.iloc[i,0] = unidecode(data.iloc[i,0]).replace('_',' ')
    data = data.reset_index(drop=True)
    data.dropna(inplace=True)

    minutes =  data['MP'].to_list()
    for i in range(len(minutes)):
        new = minutes[i].split(':')
        res = float(new[0])+(float(new[1])/60)
        minutes[i] = res
    data['MP'] = minutes
    data.columns = ['player', 'G', 'date', 'age', 'team', 'H/A', 'opp', 'W/L', 'GS', 'MP', 'FG',
        'FGA', 'FG%', '3P', '3PA', '3P%', 'FT', 'FTA', 'FT%', 'ORB', 'DRB',
        'TRB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS', 'GmSc', '+/-', 'pos','season']
    home = data['H/A'].values
    for i in range(len(home)):
        if home[i] == '@':
            home[i] = 0
        else:
            home[i] = 1
    data['H/A'] = home
    data = data.replace('CHO','CHA')
    data = data.replace('PHO','PHX')
    data= data.replace('BRK','BKN')

    data['W/L'] = data['W/L'].str.extract(r"\(([-+]?\d+)\)").astype(int)
    KM_vals = pd.read_csv('./reference_data/KM_vals.csv',index_col=0)
    KM_dict = dict(zip(KM_vals.Player,KM_vals.KM))
    temp = []
    for p in data.player.values:
        if p[0] in KM_dict:
            temp.append(KM_dict[p[0]])
        else:
            temp.append(15)
    data['KM'] = temp
    data.to_csv(f'/GIthub/NBA_betting_model/game_logs/data_{year}.csv',index=False)