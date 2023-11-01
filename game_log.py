import pandas as pd
from scipy.stats import poisson
import matplotlib.pyplot as plt

def load_current_line(path,key,time) -> pd.DataFrame:
    df = pd.read_csv(path,index_col=0).sort_values(by=time,ascending=False)
    return df.loc[df[time]== df[time].max()].reset_index(drop=True)

def get_line(player, pp_stat, lines):
    guy = lines.loc[lines["player"] == player]
    pt_lines = guy.loc[guy["stat"] == pp_stat]
    return pt_lines

class GameLog:
    def __init__(self, df):
        self.game_log = df
        self.game_log["date"] = pd.to_datetime(self.game_log["date"], format="%Y-%m-%d")
        self.game_log["rest"] = self.game_log.groupby("player")["date"].diff().dt.days
        self.game_log['rest'] = self.game_log['rest'].fillna(5)
        self.game_log['series'] = self.game_log['series'].fillna('RS')
        self.game_log['season'] = self.game_log['season'].astype(str)

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
        #color and marker keys for graph
        season_colors = {
            0: "#FFB632",
            1: "#007F94",
            2: "#EED78D",
            3: "#C22B26",
            4: "#7D48B2",
        }

        series_markers = {
            "WC1": "^",  # Circle marker
            "WCS": "^",  # Triangle marker
            "WCF": "^",  # Square marker
            "FIN": "^",  # X marker
            'RS"': "o",
        }
        num_games = 82

        mov = self.moving_avg(player, cat, window)
        points = self.get_stat(player, cat)
        player_lines = get_line(player, cat, lines)
        player_df = self.game_log.loc[self.game_log.player == player].reset_index(drop=True)
        player_df['stat_val'] = points.values
        player_df['mov'] = mov.values
        player_df= player_df.iloc[-num_games:].reset_index(drop=True)

        print(cat)
        if player_lines.empty == False:
            line = player_lines["line"].iloc[0]
            print("line:", line)
            self.print_prob(player, line, cat)
            self.print_prob(player, line, cat, games=10)
            plt.axhline(line, color="r", linestyle="--", label="line")
        print("avg:", round(points.mean(), 1))
        x = range(len(points))

        #plotting different marker and color by season/playoffs
        for (season, series), group in player_df.groupby(["season", "series"]):
            color = season_colors.get(int(season) % 5, "blue")
            marker = series_markers.get(series, "^")
            plt.scatter(group.index, group["stat_val"], color=color, marker=marker)

        #plotting moving avg, line, season avg.
        plt.plot(player_df.index, player_df.stat_val, color="g", linestyle=(0, (1, 6)))  # game line
        plt.plot(player_df.index, player_df.mov, label="moving average")  # moving average
        plt.axhline(player_df.loc[player_df.season=='2024'].stat_val.mean(), color="y", linestyle="-", label="season average")
        plt.ylabel(cat)
        plt.xlabel("Game #")
        plt.title(player)
        plt.legend()
        plt.style.use('dark_background')
        plt.show()
        return
    
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