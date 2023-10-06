#getting fantasy site lines
#removing weird lines like series, half of quarter
import pandas as pd
import datetime as dt
today = dt.datetime.today()
pp_lines = pd.read_csv(f'Lines/full_lines_{today.year}_{today.month}_{today.day}',index_col=0)
dog_lines = pd.read_csv(f'Lines/doglines{today.month}_{today.day}',index_col=0)
pp_lines = pp_lines.loc[~pp_lines['League'].isin([250,84,251,231,192,193,227])]
#parlay = pd.read_csv(f'Lines/parlaylines{today.month}_{today.day}',index_col=0)

#finding where prizepicks and underdog are different
fantasy = pp_lines.merge(dog_lines, on=['Player','Stat','Date'],how='inner',suffixes=('_pp','_dog'))
fantasy['difference'] = ((fantasy['Line_pp'] - fantasy['Line_dog']))/fantasy['Line_pp']
fantasy = fantasy.sort_values(by='difference')
fantasy.sample(3)

temp = fantasy.loc[(fantasy['difference'] != 0.0)]
temp = temp.loc[temp.Stat != 'Hitter Fantasy Score'].sort_values(by='difference')
temp = temp[['Player','Line_pp','Line_dog','Stat', 'difference',  'Date',
       'League_dog', 'Team_dog' ]]
temp.to_csv(f'bets/fantasy_bets_test.csv')

temp.loc[temp.Stat != 'Hitter Fantasy Score']

temp.loc[temp.League_dog == 'ESPORTS']

#underdog for now
fullpdf = pd.read_csv('Lines/unabated_2023_10_6.csv',index_col=0)
fullpdf.rename({'player':'Player','line':'Line','stat':'Stat'},inplace=True)
new = fullpdf.merge(pp_lines, on=['Player','Stat','Line'],how='inner').sort_values(by='o_Prob')
new.to_csv(f'bets/bets_{str(today)}.csv')
new= new.round(3)

new = new.merge(dog_lines, on=['Player','Stat'],how='inner',suffixes=('_pp','_dog'))
new['difference'] = ((new['Line_pp'] - new['Line_dog']))/new['Line_pp']
new

new.merge(temp, on=['Player','Stat','Line_pp'],how='inner')

new.columns

new[['Player', 'Stat', 'Line_pp', 'Line_dog', 'o_Prob', 'u_Prob','Date_pp','difference']].tail(20)

import yagmail
import os

attachment = os.path.abspath(f"bets/bets_{today}.csv")

send = True


if send == True:
    with open(attachment, "rb") as f:
        # send the email with the file object as an attachment

        yag = yagmail.SMTP("sharedwestover@gmail.com", oauth2_file="secrets.json")
        yag.send(subject=f"BETS! {str(today)}",attachments=f)
        
    attachment = os.path.abspath(f"bets/fantasy_bets_test.csv")
