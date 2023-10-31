import pandas as pd
from scipy.stats import poisson
import matplotlib.pyplot as plt

def load_current_line(path,key,time) -> pd.DataFrame:
    df = pd.read_csv(path,index_col=0).sort_values(by=time,ascending=False)
    return df.groupby(key).first().reset_index()

def get_line(player, pp_stat, lines):
    guy = lines.loc[lines["player"] == player]
    pt_lines = guy.loc[guy["stat"] == pp_stat]
    return pt_lines

class GameLog:
    def __init__(self, df):
        self.game_log = df
        self.game_log["date"] = pd.to_datetime(self.game_log["date"], format="%Y-%m-%d")
        self.game_log["rest"] = self.game_log.groupby("player")["date"].diff().dt.days
        self.game_log = self.game_log.fillna(5)

    def get_stat(self, player, category) -> list[float]:
        stats = self.game_log
        stats = stats.loc[stats["player"] == player]
        x = category.split("+")
        points = stats[x[0]]
        for i in range(len(x) - 1):
            points = points + stats[x[i + 1]]
        return points.to_list()
    

    def moving_avg(self, player, cat, window_size=10) -> pd.Series:
        # getting relevant stat category series
        data = self.game_log
        data = data.loc[data["player"] == player]
        x = cat.split("+")
        total = data[x[0]]

        # summing if category is multi stat
        for i in range(len(x) - 1):
            total = total + data[x[i + 1]]
            print(i)
        moving = total.rolling(window=window_size, min_periods=1).mean()
        return moving.reset_index(drop=True)

    def get_stat(self, player, category, stats=None) -> pd.Series:
        stats = self.game_log
        stats = stats.loc[stats["player"] == player]
        x = category.split("+")
        points = stats[x[0]]
        for i in range(len(x) - 1):
            points = points + stats[x[i + 1]]
        return points

    def print_prob(self, player, line, cat, stats=None, games=None) -> None:
        stats = self.game_log
        if games == None:
            series = self.get_stat(player, cat, stats).reset_index(drop=True)
        else:
            series = self.get_stat(player, cat, stats)[-games:]
        p = (series > line).sum()
        n = len(series)
        print(
            f"{player} hits the {cat} line {p}/{n} times or", round(100 * p / n, 2), "%"
        )
        return

    def graph_stat(self, player, cat, window, lines) -> None:
        print(cat)
        mov = self.moving_avg(player, cat, window)
        points = self.get_stat(player, cat)
        print(player,cat)
        display(lines)
        player_lines = get_line(player, cat, lines)
        if player_lines.empty == False:
            line = player_lines['line'].iloc[0]
            print("line:", line)
            self.print_prob(player, line, cat)
            self.print_prob(player, line, cat, games=10)
            plt.axhline(line, color="r", linestyle="--", label="line")
        x = range(len(points))
        plt.scatter(x, points, color="g", label=f"{cat}")  # games
        plt.plot(x, points, color="g", linestyle=(0, (3, 6)))  # game line
        plt.plot(x, mov, label="moving average")  # moving average
        plt.axhline(points.mean(), color="y", linestyle="-", label="season average")
        plt.ylabel(cat)
        plt.xlabel("Game #")
        plt.title(player)
        plt.legend()
        plt.show()
        print("avg:", round(points.mean(), 1))

    def dynamic(self, guy, cat, span=8) -> pd.Series:
        stats = self.game_log
        series = self.get_stat(guy, cat, stats)
        return series.ewm(span=span).mean()  # hyperparam

    def get_game(self, player, date, stats=None) -> pd.DataFrame:
        stats = self.game_log
        mask = stats["date"] == pd.Timestamp(date)
        return stats.loc[(stats["player"] == player) & mask]

    def get_pos(self, guy) -> str:
        stats = self.game_log
        return stats.loc[stats["player"] == guy]["pos"].values[0]

    def get_rolling_hit_rate(self, player, line, cat, last_n=None) -> float:
        # need to fix eventually to account for szn
        stats = self.game_log
        if last_n == None:
            window = len(stats)
        else:
            window = last_n
        series = self.get_stat(player, cat, stats)
        hit_rate = (series > line).rolling(window=window, min_periods=1).mean() * 100
        return hit_rate

    def best_odds(self, lines,schedule) -> pd.DataFrame:
        data = self.game_log
        date = pd.Timestamp(lines["date"].iloc[0]).strftime("%Y-%m-%d")
        home_teams = schedule.loc[schedule["date"] == date]["home"].values
        player_lines = lines.iloc[:, 0]
        player_idx = data["player"].unique()
        vals = []
        for i in range(len(player_lines)):
            player = lines['player'].iloc[i]
            if player in player_idx:
                cat = lines['stat'].iloc[i]
                opp = lines['team'].iloc[i]
                line = lines['line'].iloc[i]
                if opp in home_teams:
                    home = 0
                else:
                    home = 1
                series = self.get_stat(player, cat)

                season = self.get_rolling_hit_rate(player, line, cat)
                l_10 = self.get_rolling_hit_rate(player, line, cat, last_n=10)

                avg = series.mean()
                mov_avg = self.dynamic(player, cat).iloc[-1]
                expected = mov_avg  # adjust(player,cat,opp,avail)
                vals.append(
                    [
                        player,
                        opp,
                        home,
                        cat,
                        round(avg, 1),
                        round(mov_avg, 1),
                        round(expected, 1),
                        line,
                        l_10.iloc[-1],
                        season.iloc[-1],
                    ]
                )
        odd = pd.DataFrame(
            vals,
            columns=[
                "player",
                "opp",
                "home",
                "stat",
                "season_avg",
                "mov_avg",
                "expected",
                "line",
                "last_10",
                "season",
            ],
        )
        odd['blend'] = odd[['last_10', 'season']].mean(axis=1)
        odd["prob"] = 1 - poisson.cdf(mu=odd["expected"], k=odd["line"])
        return odd