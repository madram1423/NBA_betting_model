#!/usr/bin/env python
# coding: utf-8

# In[73]:


import numpy as np
import pandas as pd
import time
import re
import random
from unidecode import unidecode


# In[74]:


from urllib.request import urlopen
from bs4 import BeautifulSoup
import requests


# In[75]:


def GET_UA():
    uastrings = ["Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.111 Safari/537.36",                "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.72 Safari/537.36",                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10) AppleWebKit/600.1.25 (KHTML, like Gecko) Version/8.0 Safari/600.1.25",                "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:33.0) Gecko/20100101 Firefox/33.0",                "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.111 Safari/537.36",                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.111 Safari/537.36",                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/600.1.17 (KHTML, like Gecko) Version/7.1 Safari/537.85.10",                "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko",                "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:33.0) Gecko/20100101 Firefox/33.0",                "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.104 Safari/537.36"                ]
 
    return random.choice(uastrings)


# In[76]:


def parse_url(url):
 
    headers = {'User-Agent': GET_UA()}
    content = None
 
    try:
        response = requests.get(url, headers=headers)
        ct = response.headers['Content-Type'].lower().strip()
 
        if 'text/html' in ct:
            content = response.content
            soup = BeautifulSoup(content,features='lxml')
        else:
            content = response.content
            soup = None
 
    except Exception as e:
        print('Error:', str(e))
 
    return content, soup, ct


# In[77]:


players = pd.read_csv('player_index.csv')
player_id = players['Player-additional'].values.tolist()
player_name = players['Player'].values.tolist()
league_num =len(player_id)
i = 0
for name in player_name:
    player_name[i] = name.replace(" ", "_")
    i = i+1
print(player_name[0:10])
print(len(player_name))


# In[78]:


base = 'https://www.basketball-reference.com/players/c/bealbr01/gamelog/'
# NBA season we will be analyzing
year = '2023'
# URL page we will scraping (see image above)
url = base+year
print(url)
# this is the HTML from the given URL
html = urlopen(url)
soup = BeautifulSoup(html)


# In[79]:


# use findALL() to get the column headers
soup.findAll('tr', limit=40)
# use getText()to extract the text we need into a list
i = 0
while i < 40:
    headers = [th.getText() for th in soup.findAll('tr', limit=40)[i].findAll('th')]
    i = i +1
    if headers:
        idx = i
        i = 41

headers = headers[1:]
print(headers)


# In[80]:


# avoid the first header row
rows = soup.findAll('tr')
player_stats = [[td.getText() for td in rows[i].findAll('td')]
            for i in range(len(rows))]
stats = pd.DataFrame(player_stats, columns = headers)

stats.dropna(subset=['Age'], inplace=True)


# In[81]:


stats


# In[82]:



def get_stats(num):
    for person in range(num):
        # NBA season we will be analyzing
        year = '2023'
        player = player_id[person]
        person = person
        base = f'https://www.basketball-reference.com/players/c/{player}/gamelog/'
        # URL page we will scraping (see image above)
        url = base+year
        print(url)
        time.sleep(3)
        # this is the HTML from the given URL
        content, soup, ct = parse_url(url)
        
        # use findALL() to get the column headers
        soup.findAll('tr', limit=40)
        # use getText()to extract the text we need into a list
        i = 0
        while i < 40:
            headers = [th.getText() for th in soup.findAll('tr', limit=40)[i].findAll('th')]
            i = i +1
            if headers:
                idx = i
                i = 41

        headers = headers[1:]

        rows = soup.findAll('tr')
        player_stats = [[td.getText() for td in rows[i].findAll('td')]
                    for i in range(len(rows))]
        stats = pd.DataFrame(player_stats, columns = headers)
        stats.dropna(inplace=True)
        stats.insert(0, 'Player', player_name[person])
        stats.index = range(len(stats))
        if person == 0:
            data_core = stats
        else:
            data_core = pd.concat([data_core,stats])
        print(person,player_name[person])
    return data_core


# In[ ]:


#test = get_stats(len(player_name))
test = get_stats(3)

# In[ ]:


# In[ ]:


test['Player'].unique()


# In[ ]:


save = test.copy(deep=True)
save.tail()


# In[ ]:


test['Date'] = pd.to_datetime(test['Date'])
data = test
for i in range(len(data)):
    data.iloc[i,0] = unidecode(data.iloc[i,0]).replace('_',' ')
    
    

    #remove special characters


# In[ ]:


data = data.reset_index(drop=True)


# In[ ]:


info = pd.read_csv('player_info')
for i in range(len(info)):
    info.iloc[i,1] = unidecode(info.iloc[i,1]).replace('_',' ')
print(data['Player'][2])

p2pos = {player:pos for player,pos in zip(info['Player'].to_list(),info['Pos'].to_list())}
pos = []
for i in range(len(data)):
    pos.append(p2pos[data.iloc[i][0]])


data['Pos'] = pos


# In[ ]:


minutes =  data['MP'].to_list()

for i in range(len(minutes)):
    new = minutes[i].split(':')
    res = float(new[0])+(float(new[1])/60)
    minutes[i] = res
data['MP'] = minutes


# In[ ]:


data.columns = [['Player', 'G', 'Date', 'Age', 'Tm', 'H/A', 'Opp', 'W/L', 'GS', 'MP', 'FG',
       'FGA', 'FG%', '3P', '3PA', '3P%', 'FT', 'FTA', 'FT%', 'ORB', 'DRB',
       'TRB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS', 'GmSc', '+/-', 'Pos']]
home = data['H/A'].values

for i in range(len(home)):
    if home[i] == '@':
        home[i] = 0
    else:
        home[i] = 1


# In[ ]:


data['H/A'] = home
data = data.replace('CHO','CHA')
data = data.replace('PHO','PHX')
data= data.replace('BRK','BKN')

WL = data['W/L'].values.astype(str)
margin = []
for i in range(len(WL)):
    input_string = WL[i][0]
    output = re.match(r"^[WL]\s*\(([-]?\d+|\+\d+)\)", input_string).group(1)
    margin.append(output)

margin[0:10]
data['W/L']=margin
data['W/L'] = data['W/L'].astype(int)
data.fillna(5)


# In[ ]:


data


# In[ ]:


data.to_csv('data_test.csv',index=False)

# In[ ]:




