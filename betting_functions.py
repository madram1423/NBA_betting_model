from scipy.stats import poisson

def get_avg(Player,games=26,cat=None,stats = None):
    if stats is None:
        stats = data
    stats = stats.loc[stats['Player']== Player]
    stats = stats.iloc[-games:,10:]
    if cat:
        stats = stats[cat]
        
    avg = stats.mean()
    print(f'Jayson Tatum average {cat} over the last {games} games: ')
    return avg

def get_stat(Player,category,stats=None):
    if stats is None:
        stats = data
    stats = stats.loc[stats['Player']==Player]
    x = category.split('+')
    points = stats[x[0]]
    for i in range(len(x)-1):
        points = points + stats[x[i+1]]
    return points.to_list()

def get_line(player,pp_stat,lines):
    guy = lines.loc[lines['Player']== player]
    pt_lines = guy.loc[guy['Stat']== pp_stat]
    return pt_lines

def moving_avg(Player,cat,window=10,stats=None):
    
    #getting relevant stat category series
    if stats is None:
        stats = data
    stats = stats.loc[stats['Player']== Player]
    x = cat.split('+')
    total = stats[x[0]]
    
    #summing if category is multi stat
    for i in range(len(x)-1):
        total = total + stats[x[i+1]]
    total = np.array(total.to_list())

    #finding moving avg
    moving = [total[0]]
    for n in range(1,window-1):
        temp = total[0:n].mean()
        moving.append(temp)
    
    for i in range(len(total)-window+1):
        temp = total[i:i+window].mean()
        moving.append(temp)
        
    return moving

def print_prob(player,line,cat,stats=None,prnt=True,games=None):
    if stats is None:
        stats = data
    series = get_stat(player,cat,stats)
    p = 0
    n = 0
    if games == None:
        for i in series:
            n = n+1
            if i > line:
                p = p+1
        if prnt == True:
            print(f'{player} hits the {cat} line {p}/{n} times or',round(p/n,2),'%')
    else:
        p = 0
        n = 0
        for i in series[-games:]:
            n = n+1
            if i > line:
                p = p+1
        if prnt == True:
            print(f'{player} hits the {cat} line {p}/{n} times in his last 10') 
    return p/n
    

def graph_stat(player,cat,window,lines):
    print(cat)
    mov = dynamic(player, cat ,window)
    points = np.array(get_stat(player,cat))
    line = get_line(player,cat,lines)
    if line.empty == False:
        line = line.iloc[0,2]
        print('line:',line)
        print_prob(player,line,cat,prnt=True)
        print_prob(player,line,cat,games=10,prnt=True)
            
        plt.axhline(line, color='r', linestyle='--',label='line')
    
    x = range(len(points))
    plt.scatter(x,points, color='g',label=f'{cat}')#games
    plt.plot(x,points, color='g',linestyle=(0, (3, 6)))#game line
    plt.plot(x,mov,label='moving average')#moving average

    plt.axhline(np.mean(points), color='y', linestyle='-',label='season average')
    plt.ylabel(cat)
    plt.xlabel('Game #')
    plt.title(player)
    plt.legend()
    plt.show()
    print('avg:',round(np.mean(points),1))
    

def find_window(guy,cat):
    series,avg = get_stat(guy,cat)

    idx = []
    for window in range(2,10):

        pred = []
        mov = []
        for i in range(len(series)):
            mov = moving_avg(guy,cat,window)
        result = (((mov-series)**2).sum())/series.mean()
        idx.append(result)
    return idx
    


def dynamic(guy,cat,window=10,stats=None):
    if stats is None:
        stats = data
    series = get_stat(guy,cat,stats)
    series = np.array(series)
    alpha = 2
    
    pred = [series[0]]
    mov = [series[0]]
    for i in range(1,window):
            predict = series[0:i].mean()
            pred.append(predict)
            mov.append(predict)
    for i in range(window,len(series)):
        prev = mov[i-1]
        current = series[i]*(alpha/(window+1)) + mov[i-1]*(1- (alpha/(window+1)))
        #mov_pred = series[i-window:i].mean()
        mov.append(current)
    return(mov)


def find_dynamic(guy,cat):
    series,avg = get_stat(guy,cat)
    series = np.array(series)
    
    idx = []
    for window in range(2,10):
        mov = dynamic(guy,cat,window)
        result = (((mov-series)**2).sum())/series.mean()
        idx.append(result)
    return idx

def get_game(player,date,stats = None):
    if stats is None:
        stats = data
    mask = (stats['Date'] == date)
    df2 = stats.loc[mask]
    df2 = df2.loc[stats['Player']==player]
    return df2 

def adjust(player,cat,opp,stats=None):
    if stats is None:
        stats = data
    pos = get_pos(player,stats=stats)
    tm = opp_stats.loc[opp_stats['Team'] == opp]
    x = cat.split('+')
    adj = []
    final = 0
    for i in range(0,len(x)):
        opp_avg = km_adj(player,x[i],opp,stats=stats)
        guy_avg = dynamic(player, x[i],stats=stats)
        res = opp_avg * guy_avg[-1]
        adj.append(res)
    for i in adj:
        final+= i
    return(final)


def best_odds(lines):
    date = lines['Date'].iloc[0]
    home_teams = schedule.loc[schedule['Date']==date]['Home'].values
    player_lines = lines.iloc[:,0]
    avail = data.loc[data['Date']< date]
    player_idx = data['Player'].unique()
    vals = []
    for i in range(len(player_lines)):
        player = lines.iloc[i,0]
        
        if player in player_idx:
            cat = lines.iloc[i,3]
            opp = lines.iloc[i,1]
            if opp in home_teams:
                home = 0
            else:
                home = 1
            mov = dynamic(player, cat ,5,avail)
            series = np.array(get_stat(player,cat))
            line = lines.iloc[i,2]
            season = print_prob(player,line,cat,stats=avail,prnt=False)
            l_10 = print_prob(player,line,cat,games=10,stats=avail,prnt=False)
            
            avg = np.mean(series)
            mov_avg = dynamic(player,cat)[-1]
            expected = adjust(player,cat,opp,avail)
            vals.append([player,opp,home,cat,round(avg,1),round(mov_avg,1),round(expected,1),line,l_10,season])
    odd = pd.DataFrame(vals,columns=['Player','Opp','Home','Stat','Season_avg','mov_avg','expected','line','Last_10','Season'])
    odd['blend'] = odd[['Last_10', 'Season']].mean(axis=1) 
    odd['Prob']= 1- poisson.cdf(mu=odd['expected'],k=odd['line'])
            
    return odd


def check(lines):
    val = []
    everything = []
    err = 0
    date = lines['Date'][0]
    avail = data.loc[data['Date']== date]
    for i in range(len(lines)):
        if i%10 == 0:
            print(i)
        player = lines['Player'][i]
        date = lines['Date'][i]
        cat = lines['Stat'][i]
        line = lines['Line'][i]
        opp = lines['Team'][i]
        game  = get_game(player,date)
        expect = adjust(player,cat,opp)
        
        if game.empty:
            print('err',player)
            err += 1
        else:
            x = get_stat(player,cat,game)
            pred_diff = expect-line
            diff_real = x-line
            if np.sign(pred_diff) == np.sign(diff_real):
                val=1
            else:
                val=0
            everything.append((expect,line,x[0],pred_diff,diff_real[0],val))
    x = np.array(everything)
    df = pd.DataFrame(np.round(x,2),columns=['pred','line','actual','pred_diff','diff_real','Win'])
    return df

def get_pos(guy,stats=None):
    if stats is None:
        stats = data
    return stats.loc[stats['Player']==guy]['Pos'].values[0]

def get_start(guy):
    return data.loc[data['Player']==guy]['GS'].values[-1]

def season_stats(player):
    stats = data.copy(deep=True)
    stats = stats.loc[stats['Player']==player]
    return stats[stat_columns].mean()

def position_diff(opp,cat):
    stats = data.copy(deep=True)
    stats = stats.loc[stats['Opp'] ==opp]
    for position in ['PG','SG','SF','PF','C']:
        frame = stats.loc[stats['Pos']==position]
        print(position,48*frame[cat].mean()/frame['MP'].mean())
    
    return frame.head(5)

def position_adj(opp,cat,player):
    position=get_pos(player)
    start = get_start(player)
    stats = data.copy(deep=True)
    stats = stats.loc[stats['GS']==start]

    stats2 = stats.loc[stats['Opp'] ==opp]

    stats2
    
    #frame is that position stats vs everyone
    #frame2 is that position vs this team
    frame = stats.loc[stats['Pos']==position]
    x = 48*frame[cat].mean()/frame['MP'].mean()
    
    frame2 = stats2.loc[stats2['Pos']==position]
    y = 48*frame2[cat].mean()/frame['MP'].mean()
    y = y/x

    return y


def home_adjust(guy,cat,home,stats=None):
    final = []
    if stats is None:
        stats = data
    stats = stats.loc[stats['Player']==guy]
    cat = cat.split('+')
    homestats = stats.loc[stats['H/A']==1][cat].mean()
    awaystats = stats.loc[stats['H/A']==0][cat].mean()
    seasonstats = stats[cat].mean()
    if home == 1:
        x = homestats.sum()/seasonstats.sum()
    else:
        x = awaystats.sum()/seasonstats.sum()
    return x

def get_KM(player,stats=None):
    if stats is None:
        stats = data
    return stats.loc[stats.Player==player].KM.values[0]

def km_adj(player,cat,opp,stats=None):
    if stats is None:
        stats =  data.copy(deep=True)
    stats = stats.reset_index()
    km = get_KM(player,stats=stats)

    stats = stats.loc[stats['KM']==km]
    stats2 = stats.loc[stats['Opp']==opp]
    
    #frame is that cluster vs everyone
    #frame2 is that cluster vs this team

    x = 48*stats[cat].mean()/stats['MP'].mean()
    
    y = 48*stats2[cat].mean()/stats2['MP'].mean()
    y = y/x
    return y

def results(final):
    bets = len(final)
    over_actual = len(final.loc[final['diff_real']>0])
    print(over_actual,bets)
    o_per = over_actual/bets
    under_actual = len(final.loc[final['diff_real']<0])
    u_per = under_actual/bets
    over_pred = len(final.loc[final['pred_diff']>0])
    o_wins = final.loc[final['pred_diff']>0]['Win'].sum()
    
    under_pred = len(final.loc[final['pred_diff']<0])
    u_wins = final.loc[final['pred_diff']<0]['Win'].sum()
    
    print(f'actual over:{over_actual}/{len(final)}, {100*o_per:.0f}%')
    print(f'actual under:{under_actual}/{len(final)}, {100*u_per:.0f}%')
    print('predicted over results',o_wins,over_pred, f'{o_wins/over_pred:.0%}')
    print('predicted under results:',u_wins,under_pred, f'{u_wins/under_pred:.0%}')
    print('overall results:',f'{(o_wins+u_wins)/bets:.0%}')
    return ((o_wins+u_wins)/bets)

def mean2prob(mean,line,side):
    over = 1- poisson.cdf(line,mean)
    push = poisson.pmf(line,mean)
    under = poisson.cdf(line,mean)-poisson.pmf(line,mean)
    if side == 'over':
        return over/(over+under)
    if side == 'under':
        return under/(over+under)

def prob2american(p):
    if p > 0.5:
        #p = 100*p
        amer = -100/(p-1)
        amer = -amer + 100
    elif p < 0.5:
        amer = 100*(1/p)
        amer = amer-100
    else:
        amer = 100
    return amer

def prob2mean(prob,line,side):
    #poisson is criteria then avg
    avg = line
    over = 1- poisson.cdf(line,avg)
    push = poisson.pmf(line,avg)
    under = poisson.cdf(line,avg)-poisson.pmf(line,avg)
    pois = over/(under+over)
    
    while abs(pois-prob) > 0.001:
        lr = avg*0.5
        over = 1- poisson.cdf(line,avg)
        push = poisson.pmf(line,avg)
        under = poisson.cdf(line,avg)-poisson.pmf(line,avg)
        if side == 'over':
            pois = over/(under+over)
            if pois < prob:
                avg = (lr*(prob-pois))+avg
            else:
                avg = avg - (pois-prob)
        else:
            pois = under/(under+over)
            if pois > prob:
                avg = (-lr*(prob-pois))+avg
            else:
                avg = avg + lr*(pois-prob)
    return(avg)