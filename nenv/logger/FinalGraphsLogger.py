from nenv.logger.AbstractLogger import AbstractLogger, ExcelLog
from typing import Union
import os
from nenv.utils.tournament_graphs import draw_heatmap
from typing import List
import numpy as np
import pandas as pd


class FinalGraphsLogger(AbstractLogger):
    """
        FinalGraphsLogger draw plots and Confusion Matrix for the evaluation of the Agent performance at the end of the
        negotiation.
    """
    domain_sep: int

    def __init__(self, log_dir: str, domain_sep: int = 15):
        super().__init__(log_dir)

        self.domain_sep = domain_sep

    def on_tournament_end(self, tournament_logs: ExcelLog, agent_names: List[str], domain_names: List[str],
                          estimator_names: List[str]):
        tournament_results = tournament_logs.to_data_frame("TournamentResults")

        if not os.path.exists(self.get_path("tournament_graphs/")):
            os.makedirs(self.get_path("tournament_graphs/"))

        self.draw_opponent_based(tournament_results, agent_names, self.get_path("tournament_graphs/"))

        for i in range(0, len(domain_names), self.domain_sep):
            end = min(len(domain_names), i + self.domain_sep)

            idx = domain_names[i:end]

            self.draw_domain_based(tournament_results, agent_names, idx, self.get_path("tournament_graphs/"),
                                   f"({i}_{end})" if len(domain_names) > self.domain_sep else "")

    def draw_opponent_based(self, tournament_results: pd.DataFrame, agent_names: list, directory: str):
        data_utility = [[None for j in range(len(agent_names))] for i in range(len(agent_names))]
        data_opp_utility = [[None for j in range(len(agent_names))] for i in range(len(agent_names))]
        data_product_score = [[None for j in range(len(agent_names))] for i in range(len(agent_names))]
        data_nash_distances = [[None for j in range(len(agent_names))] for i in range(len(agent_names))]
        data_social_welfare = [[None for j in range(len(agent_names))] for i in range(len(agent_names))]
        data_time = [[None for j in range(len(agent_names))] for i in range(len(agent_names))]
        data_acceptance_rate = [[None for j in range(len(agent_names))] for i in range(len(agent_names))]

        for i, agent_name_a in enumerate(agent_names):
            for j, agent_name_b in enumerate(agent_names):
                # Individual Utility
                rows_utility = tournament_results.loc[(tournament_results["AgentA"] == agent_name_a) &
                                                      (tournament_results["AgentB"] == agent_name_b),
                "AgentAUtility"].to_list()

                rows_utility.extend(tournament_results.loc[(tournament_results["AgentA"] == agent_name_b) &
                                                           (tournament_results["AgentB"] == agent_name_a),
                "AgentBUtility"].to_list())

                # Opponent Utility

                rows_opp_utility = tournament_results.loc[(tournament_results["AgentA"] == agent_name_a) &
                                                          (tournament_results["AgentB"] == agent_name_b),
                "AgentBUtility"].to_list()

                rows_opp_utility.extend(tournament_results.loc[(tournament_results["AgentA"] == agent_name_b) &
                                                               (tournament_results["AgentB"] == agent_name_a),
                "AgentAUtility"].to_list())

                # Nash Distance

                row_nash_distances = tournament_results.loc[(tournament_results["AgentA"] == agent_name_a) &
                                                            (tournament_results["AgentB"] == agent_name_b),
                "NashDistance"].to_list()

                row_nash_distances.extend(tournament_results.loc[(tournament_results["AgentA"] == agent_name_b) &
                                                                 (tournament_results["AgentB"] == agent_name_a),
                "NashDistance"].to_list())

                # Acceptance Time

                rows_acceptance = tournament_results.loc[(tournament_results["AgentA"] == agent_name_a) &
                                                         (tournament_results["AgentB"] == agent_name_b) &
                                                         (tournament_results["Result"] == "Acceptance"),
                "Time"].to_list()

                rows_acceptance.extend(tournament_results.loc[(tournament_results["AgentA"] == agent_name_b) &
                                                              (tournament_results["AgentB"] == agent_name_a) &
                                                              (tournament_results["Result"] == "Acceptance"),
                "Time"].to_list())

                if len(rows_utility) == 0:
                    continue
                else:
                    data_utility[i][j] = np.mean(rows_utility)

                    data_opp_utility[i][j] = np.mean(rows_opp_utility)

                    data_product_score[i][j] = np.mean(
                        [rows_utility[k] * rows_opp_utility[k] for k in range(len(rows_utility))])

                    data_social_welfare[i][j] = np.mean(
                        [rows_utility[k] + rows_opp_utility[k] for k in range(len(rows_utility))])

                    data_nash_distances[i][j] = np.mean(row_nash_distances)

                    data_time[i][j] = np.mean(rows_acceptance)

                    data_acceptance_rate[i][j] = len(rows_acceptance) / len(rows_utility)

        sorted_agent_names, sorted_map = sort_y_axis(agent_names, agent_names, data_utility)

        draw_heatmap(sorted_map, sorted_agent_names, sorted_agent_names,
                     os.path.join(directory, "opponent_based_individual_utility"), "Opponent", "Agent")

        sorted_agent_names, sorted_map = sort_y_axis(agent_names, agent_names, data_opp_utility)

        draw_heatmap(sorted_map, sorted_agent_names, sorted_agent_names,
                     os.path.join(directory, "opponent_based_opponent_utility"), "Opponent", "Agent")

        sorted_agent_names, sorted_map = sort_y_axis(agent_names, agent_names, data_product_score)

        draw_heatmap(sorted_map, sorted_agent_names, sorted_agent_names,
                     os.path.join(directory, "opponent_based_product_score"), "Opponent", "Agent")

        sorted_agent_names, sorted_map = sort_y_axis(agent_names, agent_names, data_social_welfare)

        draw_heatmap(sorted_map, sorted_agent_names, sorted_agent_names,
                     os.path.join(directory, "opponent_based_social_welfare"), "Opponent", "Agent", vmax=True)

        sorted_agent_names, sorted_map = sort_y_axis(agent_names, agent_names, data_nash_distances, descending=False)

        draw_heatmap(sorted_map, sorted_agent_names, sorted_agent_names,
                     os.path.join(directory, "opponent_based_nash_distances"), "Opponent", "Agent", reverse=True,
                     vmax=True)

        sorted_agent_names, sorted_map = sort_y_axis(agent_names, agent_names, data_time)

        draw_heatmap(sorted_map, sorted_agent_names, sorted_agent_names,
                     os.path.join(directory, "opponent_based_agreement_time"), "Opponent", "Agent")

        sorted_agent_names, sorted_map = sort_y_axis(agent_names, agent_names, data_acceptance_rate)

        draw_heatmap(sorted_map, sorted_agent_names, sorted_agent_names,
                     os.path.join(directory, "opponent_based_agreement_rate"), "Opponent", "Agent", fmt=".0%")

    def draw_domain_based(self, tournament_results: pd.DataFrame, agent_names: list, domain_names: list, directory: str,
                          domain_set: str = ""):
        data_utility = [[None for j in range(len(domain_names))] for i in range(len(agent_names))]
        data_opp_utility = [[None for j in range(len(domain_names))] for i in range(len(agent_names))]
        data_product_score = [[None for j in range(len(domain_names))] for i in range(len(agent_names))]
        data_nash_distances = [[None for j in range(len(domain_names))] for i in range(len(agent_names))]
        data_social_welfare = [[None for j in range(len(domain_names))] for i in range(len(agent_names))]
        data_time = [[None for j in range(len(domain_names))] for i in range(len(agent_names))]
        data_acceptance_rate = [[None for j in range(len(domain_names))] for i in range(len(agent_names))]

        for i, agent_name in enumerate(agent_names):
            for j, domain_name in enumerate(domain_names):
                # Individual Utility
                rows_utility = tournament_results.loc[(tournament_results["AgentA"] == agent_name) &
                                                      (tournament_results["DomainName"] == domain_name),
                "AgentAUtility"].to_list()

                rows_utility.extend(tournament_results.loc[(tournament_results["AgentB"] == agent_name) &
                                                           (tournament_results["DomainName"] == domain_name),
                "AgentBUtility"].to_list())

                # Opponent Utility

                rows_opp_utility = tournament_results.loc[(tournament_results["AgentB"] == agent_name) &
                                                          (tournament_results[
                                                               "DomainName"] == domain_name), "AgentAUtility"].to_list()

                rows_opp_utility.extend(tournament_results.loc[(tournament_results["AgentA"] == agent_name) &
                                                               (tournament_results["DomainName"] == domain_name),
                "AgentBUtility"].to_list())

                # Nash Distance

                row_nash_distances = tournament_results.loc[(tournament_results["AgentA"] == agent_name) &
                                                            (tournament_results["DomainName"] == domain_name),
                "NashDistance"].to_list()

                row_nash_distances.extend(tournament_results.loc[(tournament_results["AgentB"] == agent_name) &
                                                                 (tournament_results["DomainName"] == domain_name),
                "NashDistance"].to_list())

                # Acceptance Times

                rows_time = tournament_results.loc[(tournament_results["AgentA"] == agent_name) &
                                                   (tournament_results["AgentB"] != agent_name) &
                                                   (tournament_results["DomainName"] == domain_name),
                "Time"].to_list()

                rows_time.extend(tournament_results.loc[(tournament_results["AgentB"] == agent_name) &
                                                        (tournament_results["AgentA"] != agent_name) &
                                                        (tournament_results["DomainName"] == domain_name),
                "Time"].to_list())

                rows_time.extend(tournament_results.loc[(tournament_results["AgentB"] == agent_name) &
                                                        (tournament_results["AgentA"] == agent_name) &
                                                        (tournament_results["DomainName"] == domain_name),
                "Time"].to_list())

                # Number of acceptance

                rows_acceptance = tournament_results.loc[(tournament_results["AgentA"] == agent_name) &
                                                         (tournament_results["AgentB"] != agent_name) &
                                                         (tournament_results["DomainName"] == domain_name) &
                                                         (tournament_results["Result"] == "Acceptance"),
                "Time"].to_list()

                rows_acceptance.extend(tournament_results.loc[(tournament_results["AgentB"] == agent_name) &
                                                              (tournament_results["AgentA"] != agent_name) &
                                                              (tournament_results["DomainName"] == domain_name) &
                                                              (tournament_results["Result"] == "Acceptance"),
                "Time"].to_list())

                rows_acceptance.extend(tournament_results.loc[(tournament_results["AgentB"] == agent_name) &
                                                              (tournament_results["AgentA"] == agent_name) &
                                                              (tournament_results["DomainName"] == domain_name) &
                                                              (tournament_results["Result"] == "Acceptance"),
                "Time"].to_list())

                if len(rows_utility) == 0:
                    continue
                else:
                    data_utility[i][j] = np.mean(rows_utility)
                    data_opp_utility[i][j] = np.mean(rows_opp_utility)
                    data_product_score[i][j] = np.mean(
                        [rows_utility[k] * rows_opp_utility[k] for k in range(len(rows_utility))])
                    data_nash_distances[i][j] = np.mean(row_nash_distances)
                    data_social_welfare[i][j] = np.mean(
                        [rows_utility[k] + rows_opp_utility[k] for k in range(len(rows_utility))])
                    data_time[i][j] = np.mean(rows_time)
                    data_acceptance_rate[i][j] = len(rows_acceptance) / len(rows_time)

        domain_names = ["Domain%s" % domain_name for domain_name in domain_names]

        if domain_set != '':
            domain_set = f"_{domain_set}"

        sorted_agent_names, sorted_map = sort_y_axis(agent_names, domain_names, data_utility)

        draw_heatmap(sorted_map, domain_names, sorted_agent_names,
                     os.path.join(directory, f"domain_based_individual_utility{domain_set}"), "Domains", "Agents")

        sorted_agent_names, sorted_map = sort_y_axis(agent_names, domain_names, data_opp_utility)

        draw_heatmap(sorted_map, domain_names, sorted_agent_names,
                     os.path.join(directory, f"domain_based_opponent_utility{domain_set}"), "Domains", "Agents")

        sorted_agent_names, sorted_map = sort_y_axis(agent_names, domain_names, data_product_score)

        draw_heatmap(sorted_map, domain_names, sorted_agent_names,
                     os.path.join(directory, f"domain_based_product_score{domain_set}"), "Domains", "Agents")

        sorted_agent_names, sorted_map = sort_y_axis(agent_names, domain_names, data_nash_distances, descending=False)

        draw_heatmap(sorted_map, domain_names, sorted_agent_names,
                     os.path.join(directory, f"domain_based_nash_distance{domain_set}"), "Domains", "Agents",
                     reverse=True, auto_scale=True)

        sorted_agent_names, sorted_map = sort_y_axis(agent_names, domain_names, data_social_welfare)

        draw_heatmap(sorted_map, domain_names, sorted_agent_names,
                     os.path.join(directory, f"domain_based_social_welfare{domain_set}"), "Domains", "Agents",
                     auto_scale=True)

        sorted_agent_names, sorted_map = sort_y_axis(agent_names, domain_names, data_time)

        draw_heatmap(sorted_map, domain_names, sorted_agent_names,
                     os.path.join(directory, f"domain_based_agreement_time{domain_set}"), "Domains", "Agents")

        sorted_agent_names, sorted_map = sort_y_axis(agent_names, domain_names, data_acceptance_rate)

        draw_heatmap(sorted_map, domain_names, sorted_agent_names,
                     os.path.join(directory, f"domain_based_agreement_rate{domain_set}"), "Domains", "Agents",
                     fmt=".0%")


def sort_y_axis(labels_y: List[str], labels_x: List[str], map_values: List[List[Union[float, None]]],
                descending: bool = True) -> (List[str], List[List[float]]):
    """
        This method sorts the map based on the mean of row.

        :param labels_y: y-axis Labels
        :param labels_x: x-axis Labels
        :param map_values: Map that will be sorted.
        :param descending: Whether the order is descending or not
        :return: Sorted list of y-axis labels and map
    """
    means = np.array([np.mean([map_values[i][j] for j in range(len(labels_x)) if map_values[i][j] is not None]) for i in range(len(labels_y))])

    indices = list(range(len(labels_y)))

    indices.sort(key=lambda i: means[i], reverse=descending)

    sorted_labels = []

    for i in indices:
        sorted_labels.append(labels_y[i])

    sorted_map = []

    both_axis = labels_y == labels_x

    for i in indices:
        row = []
        idx = indices if both_axis else list(range(len(labels_x)))
        for j in idx:
            row.append(map_values[i][j])

        sorted_map.append(row)

    return sorted_labels, sorted_map
