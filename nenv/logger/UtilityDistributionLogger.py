import warnings
from nenv.Preference import domain_loader
from nenv.BidSpace import BidSpace, BidPoint
from nenv.logger.AbstractLogger import AbstractLogger, SessionLogs, Session, LogRow, ExcelLog
from typing import Union, Optional
from nenv.utils.tournament_graphs import plt, DRAWING_FORMAT
from typing import List
import numpy as np
import os
import matplotlib
matplotlib.use('Agg')  # Agg backend for file-based rendering


class UtilityDistributionLogger(AbstractLogger):
    """
        UtilityDistributionLogger logs the offered utility distribution and draws them.
    """
    def on_session_end(self, final_row: LogRow, session: Union[Session, SessionLogs]) -> LogRow:
        # Collect utility values
        utility_a, utility_b = [], []
        opp_utility_a, opp_utility_b = [], []

        for log_row in session.session_log.log_rows["Session"]:
            if log_row["Action"] != "Offer":
                continue

            if log_row["Who"] == 'A':
                utility_a.append(log_row["AgentAUtility"])
                opp_utility_a.append(log_row["AgentBUtility"])
            else:
                utility_b.append(log_row["AgentBUtility"])
                opp_utility_b.append(log_row["AgentAUtility"])

        return {"UtilityDist": {
            "MeanAgentUtilityA": np.mean(utility_a) if len(utility_a) > 0 else 0.,
            "MeanAgentUtilityB": np.mean(utility_b) if len(utility_b) > 0 else 0.,
            "MeanOpponentUtilityA": np.mean(opp_utility_a) if len(opp_utility_a) > 0 else 0.,
            "MeanOpponentUtilityB": np.mean(opp_utility_b) if len(opp_utility_b) > 0 else 0.,
            "StdAgentUtilityA": np.std(utility_a) if len(utility_a) > 0 else 0.,
            "StdAgentUtilityB": np.std(utility_b) if len(utility_b) > 0 else 0.,
            "StdOpponentUtilityA": np.std(opp_utility_a) if len(opp_utility_a) > 0 else 0.,
            "StdOpponentUtilityB": np.std(opp_utility_b) if len(opp_utility_b) > 0 else 0.,
            "MaxAgentUtilityA": np.max(utility_a) if len(utility_a) > 0 else 0.,
            "MaxAgentUtilityB": np.max(utility_b) if len(utility_b) > 0 else 0.,
            "MaxOpponentUtilityA": np.max(opp_utility_a) if len(opp_utility_a) > 0 else 0.,
            "MaxOpponentUtilityB": np.max(opp_utility_b) if len(opp_utility_b) > 0 else 0.,
            "MinAgentUtilityA": np.min(utility_a) if len(utility_a) > 0 else 0.,
            "MinAgentUtilityB": np.min(utility_b) if len(utility_b) > 0 else 0.,
            "MinOpponentUtilityA": np.min(opp_utility_a) if len(opp_utility_a) > 0 else 0.,
            "MinOpponentUtilityB": np.min(opp_utility_b) if len(opp_utility_b) > 0 else 0.,
        }}

    def on_tournament_end(self, tournament_logs: ExcelLog, agent_names: List[str], domain_names: List[str],
                          estimator_names: List[str]):

        self.draw_agent_opponent_utility(tournament_logs, agent_names, self.log_dir, False)

        if not os.path.exists(self.get_path("domains/")):
            os.makedirs(self.get_path("domains/"))

        for domain in domain_names:
            domain_name = "Domain%s" % domain
            domain_dir = self.get_path("domains/%s/" % domain_name)

            if not os.path.exists(domain_dir):
                os.makedirs(domain_dir)

            self.draw_agent_opponent_utility(tournament_logs, agent_names, domain_dir, True, domain)

    def draw_agent_opponent_utility(self, tournament_logs: ExcelLog, agent_names: list, directory: str,
                                    draw_pareto: bool, target_domain_id: Optional[str] = None):
        agent_mean_utilities = {}
        opponent_mean_utilities = {}

        agent_min_utilities = {}
        opponent_min_utilities = {}

        agent_max_utilities = {}
        opponent_max_utilities = {}

        csv_infos = []

        domain_id = -1

        for agent_name in agent_names:
            agent_mean_utilities[agent_name] = []
            opponent_mean_utilities[agent_name] = []

            agent_min_utilities[agent_name] = []
            opponent_min_utilities[agent_name] = []

            agent_max_utilities[agent_name] = []
            opponent_max_utilities[agent_name] = []

        for i, row in enumerate(tournament_logs.log_rows["UtilityDist"]):
            domain_id = tournament_logs.log_rows["TournamentResults"][i]["DomainName"]

            if target_domain_id is not None and domain_id != target_domain_id:
                continue

            agent_a = tournament_logs.log_rows["TournamentResults"][i]["AgentA"]
            agent_b = tournament_logs.log_rows["TournamentResults"][i]["AgentB"]

            agent_mean_utilities[agent_a].append(row["MeanAgentUtilityA"])
            agent_mean_utilities[agent_b].append(row["MeanAgentUtilityB"])

            opponent_mean_utilities[agent_a].append(row["MeanOpponentUtilityA"])
            opponent_mean_utilities[agent_b].append(row["MeanOpponentUtilityB"])

            agent_min_utilities[agent_a].append(row["MinAgentUtilityA"])
            agent_min_utilities[agent_b].append(row["MinAgentUtilityB"])

            opponent_min_utilities[agent_a].append(row["MinOpponentUtilityA"])
            opponent_min_utilities[agent_b].append(row["MinOpponentUtilityB"])

            agent_max_utilities[agent_a].append(row["MaxAgentUtilityA"])
            agent_max_utilities[agent_b].append(row["MaxAgentUtilityB"])

            opponent_max_utilities[agent_a].append(row["MaxOpponentUtilityA"])
            opponent_max_utilities[agent_b].append(row["MaxOpponentUtilityB"])

        for agent_name in opponent_mean_utilities:
            x = np.mean(opponent_mean_utilities[agent_name])
            y = np.mean(agent_mean_utilities[agent_name])
            x_err = [[abs(x - np.min(opponent_min_utilities[agent_name]))],
                     [abs(np.max(opponent_max_utilities[agent_name]) - x)]]

            y_err = [[abs(y - np.min(agent_min_utilities[agent_name]))],
                     [abs(np.max(agent_max_utilities[agent_name]) - y)]]

            csv_infos.append({
                "AgentName": agent_name,
                "OpponentMeanUtility": x,
                "AgentMeanUtility": y,
                "OpponentMinUtility": x_err[0][0],
                "AgentMinUtility": y_err[0][0],
                "OpponentMaxUtility": x_err[1][0],
                "AgentMaxUtility": y_err[1][0],
            })

            plt.errorbar(x, y, xerr=np.array(x_err), yerr=np.array(y_err), label=agent_name, marker='o', markersize=5.)

        if draw_pareto:
            pareto, nash_point, kalai_point = self.get_pareto_nash_kalai(domain_id)

            nash = [nash_point.utility_a, nash_point.utility_b]
            kalai = [kalai_point.utility_a, kalai_point.utility_b]

            plt.plot(pareto[:, 0], pareto[:, 1], "-*k", label="Pareto")
            plt.scatter(nash[0], nash[1], c="r", marker="^", label="Nash", s=75)
            plt.scatter(kalai[0], kalai[1], c="r", marker="o", label="Kalai", s=100)

        plt.xlabel("Opponent Utility", fontsize=18)
        plt.ylabel("Agent Utility", fontsize=18)

        plt.title("Utility Distribution", fontsize=20)

        plt.legend()

        fig = plt.gcf()
        fig.set_size_inches(18.5, 10.5)

        plt.tight_layout()

        global DRAWING_FORMAT
        DRAWING_FORMAT = os.getenv('DRAWING_FORMAT', "matplotlib-PNG")

        if DRAWING_FORMAT == "matplotlib-PNG":
            plt.savefig(os.path.join(directory, "utility_distribution.png"), dpi=1200)
        elif DRAWING_FORMAT == "matplotlib-SVG":
            plt.savefig(os.path.join(directory, "utility_distribution.svg"), dpi=1200)
        else:
            warnings.warn("UtilityDistributionLogger does not support `plotly` format in this version. " +
                          "Format for utility distribution is set as `matplotlib-SVG`", UserWarning)

            plt.savefig(os.path.join(directory, "utility_distribution.png"), dpi=1200)
        plt.close()

        # To CSV
        with open(os.path.join(directory, "utility_distribution.csv"), "w") as f:
            f.write("AgentName;OpponentMeanUtility;AgentMeanUtility;OpponentMinUtility;AgentMinUtility;" +
                    "OpponentMaxUtility;AgentMaxUtility;\n")

            for info_row in csv_infos:
                f.write(str(info_row["AgentName"]) + ";")
                f.write(str(info_row["OpponentMeanUtility"]) + ";")
                f.write(str(info_row["AgentMeanUtility"]) + ";")
                f.write(str(info_row["OpponentMinUtility"]) + ";")
                f.write(str(info_row["AgentMinUtility"]) + ";")
                f.write(str(info_row["OpponentMaxUtility"]) + ";")
                f.write(str(info_row["AgentMaxUtility"]) + ";\n")

    @staticmethod
    def get_pareto_nash_kalai(domain_no: str) -> (np.ndarray, BidPoint, BidPoint):
        preference_A, preference_B = domain_loader(domain_no)

        bid_space = BidSpace(preference_A, preference_B)

        pareto_points = bid_space.pareto

        pareto = []

        for pareto_point in pareto_points:
            pareto.append([pareto_point.utility_a, pareto_point.utility_b])

        return np.array(pareto), bid_space.nash_point, bid_space.kalai_point
