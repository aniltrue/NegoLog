from nenv.logger.AbstractLogger import AbstractLogger, ExcelLog
from typing import List
import numpy as np
import pandas as pd


class TournamentSummaryLogger(AbstractLogger):
    """
        TournamentSummaryLogger summarize the tournament results for the performance analysis of agents.
    """

    def on_tournament_end(self, tournament_logs: ExcelLog, agent_names: List[str], domain_names: List[str],
                          estimator_names: List[str]):
        summary = pd.DataFrame(
            columns=["AgentName",
                     "Avg.Utility", "Median Utility", "Std.Utility",
                     "Avg.OpponentUtility", "Median OpponentUtility", "Std.OpponentUtility",
                     "Avg.AcceptanceTime", "Median AcceptanceTime", "Std.AcceptanceTime",
                     "Avg.Round", "Median Round", "Std.Round",
                     "Avg.ProductScore", "Median ProductScore", "Std.ProductScore",
                     "Avg.SocialWelfare", "Median SocialWelfare", "Std.SocialWelfare",
                     "Avg.NashDistance", "Median NashDistance", "Std.NashDistance",
                     "Avg.KalaiDistance", "Median KalaiDistance", "Std.KalaiDistance",
                     "AcceptanceRate", "Count", "Acceptance", "Failed", "Error", "TimedOut",
                     "SelfError", "SelfTimedOut"]
        )

        summary_acceptance = pd.DataFrame(
            columns=["AgentName",
                     "Avg.Utility", "Median Utility", "Std.Utility",
                     "Avg.OpponentUtility", "Median OpponentUtility", "Std.OpponentUtility",
                     "Avg.AcceptanceTime", "Median AcceptanceTime", "Std.AcceptanceTime",
                     "Avg.Round", "Median Round", "Std.Round",
                     "Avg.ProductScore", "Median ProductScore", "Std.ProductScore",
                     "Avg.SocialWelfare", "Median SocialWelfare", "Std.SocialWelfare",
                     "Avg.NashDistance", "Median NashDistance", "Std.NashDistance",
                     "Avg.KalaiDistance", "Median KalaiDistance", "Std.KalaiDistance",
                     "Count"]
        )

        summary_without_error = pd.DataFrame(
            columns=["AgentName",
                     "Avg.Utility", "Median Utility", "Std.Utility",
                     "Avg.OpponentUtility", "Median OpponentUtility", "Std.OpponentUtility",
                     "Avg.AcceptanceTime", "Median AcceptanceTime", "Std.AcceptanceTime",
                     "Avg.Round", "Median Round", "Std.Round",
                     "Avg.ProductScore", "Median ProductScore", "Std.ProductScore",
                     "Avg.SocialWelfare", "Median SocialWelfare", "Std.SocialWelfare",
                     "Avg.NashDistance", "Median NashDistance", "Std.NashDistance",
                     "Avg.KalaiDistance", "Median KalaiDistance", "Std.KalaiDistance",
                     "AcceptanceRate", "Count", "Acceptance", "Failed"]
        )

        tournament_results = tournament_logs.to_data_frame("TournamentResults")
        
        tournament_acceptance_results = tournament_results.loc[(tournament_results["Result"] == "Acceptance")]

        tournament_without_error_results = tournament_results.loc[
            (tournament_results["Result"] != "Error") & (tournament_results["Result"] != "TimedOut")]

        for i, agent_name in enumerate(agent_names):
            # Summary
            summary.loc[i] = self.get_row(agent_name, tournament_results)
            
            # Summary only Acceptance

            summary_acceptance.loc[i] = self.get_row(agent_name, tournament_acceptance_results)
                
            # Summary without Error
            
            summary_without_error.loc[i] = self.get_row(agent_name, tournament_without_error_results)

        summary.sort_values(by="Avg.Utility", inplace=True, ascending=False)

        summary_acceptance.sort_values(by="Avg.Utility", inplace=True, ascending=False)

        summary_without_error.sort_values(by="Avg.Utility", inplace=True, ascending=False)

        with pd.ExcelWriter(self.get_path("summary.xlsx")) as f:
            summary.to_excel(f, sheet_name="Summary", index=False)
            summary_acceptance.to_excel(f, sheet_name="Summary Acceptance", index=False)
            summary_without_error.to_excel(f, sheet_name="Summary without Error", index=False)

    @staticmethod
    def get_row(agent_name: str, tournament_results: pd.DataFrame) -> dict:
        # Utility
        utilities = tournament_results.loc[(tournament_results["AgentA"] == agent_name), "AgentAUtility"].to_list()
        utilities.extend(
            tournament_results.loc[(tournament_results["AgentB"] == agent_name), "AgentBUtility"].to_list())

        if len(utilities) == 0:  # No data can be found.
            return  {
                "AgentName": agent_name,
                "Avg.Utility": 0.,
                "Median Utility": 0.,
                "Std.Utility": 0.,
                "Avg.OpponentUtility": 0.,
                "Median OpponentUtility": 0.,
                "Std.OpponentUtility": 0.,
                "Avg.AcceptanceTime": 0.,
                "Median AcceptanceTime": 0.,
                "Std.AcceptanceTime": 0.,
                "Avg.Round": 0.,
                "Median Round": 0.,
                "Std.Round": 0.,
                "Avg.ProductScore": 0.,
                "Median ProductScore": 0.,
                "Std.ProductScore": 0.,
                "Avg.SocialWelfare": 0.,
                "Median SocialWelfare": 0.,
                "Std.SocialWelfare": 0.,
                "Avg.NashDistance": 0.,
                "Median NashDistance": 0.,
                "Std.NashDistance": 0.,
                "Avg.KalaiDistance": 0.,
                "Median KalaiDistance": 0.,
                "Std.KalaiDistance": 0.,
                "AcceptanceRate": 0.,
                "Count": 0.,
                "Acceptance": 0.,
                "Failed": 0.,
                "Error": 0.,
                "TimedOut": 0.,
                "SelfError": 0.,
                "SelfTimedOut": 0.
            }


        # Opponent Utility
        opponent_utilities = tournament_results.loc[(tournament_results["AgentA"] == agent_name), "AgentBUtility"]. \
            to_list()
        opponent_utilities.extend(
            tournament_results.loc[(tournament_results["AgentB"] == agent_name), "AgentAUtility"].to_list())

        # Acceptance Times
        acceptance_times = tournament_results.loc[
            ((tournament_results["AgentA"] == agent_name) | (tournament_results["AgentB"] == agent_name)) & (
                    tournament_results["Result"] == "Acceptance"), "Time"].to_list()

        # Rounds
        rounds = tournament_results.loc[
            ((tournament_results["AgentA"] == agent_name) | (tournament_results["AgentB"] == agent_name))
            , "Round"].to_list()

        # Nash Distances
        nash_distances = tournament_results.loc[(tournament_results["AgentA"] == agent_name) | (
                tournament_results["AgentB"] == agent_name), "NashDistance"].to_list()
        
        # Kalai Distances
        kalai_distances = tournament_results.loc[(tournament_results["AgentA"] == agent_name) | (
                tournament_results["AgentB"] == agent_name), "KalaiDistance"].to_list()

        # Product Score
        product_score = tournament_results.loc[(tournament_results["AgentA"] == agent_name) | (
                tournament_results["AgentB"] == agent_name), "ProductScore"].to_list()
        
        # Social Welfare
        social_welfare = tournament_results.loc[(tournament_results["AgentA"] == agent_name) | (
                tournament_results["AgentB"] == agent_name), "SocialWelfare"].to_list()

        # Number of Failed
        failed_count = len(tournament_results.loc[
            ((tournament_results["AgentA"] == agent_name) | (tournament_results["AgentB"] == agent_name)) & (
                    tournament_results["Result"] == "Failed"), "Time"].to_list())

        # Number of Error
        error_count = len(tournament_results.loc[
            ((tournament_results["AgentA"] == agent_name) | (tournament_results["AgentB"] == agent_name)) & (
                    tournament_results["Result"] == "Error"), "Time"].to_list())

        # Number of Timed out
        timed_out_count = len(tournament_results.loc[
            ((tournament_results["AgentA"] == agent_name) | (tournament_results["AgentB"] == agent_name)) & (
                    tournament_results["Result"] == "TimedOut"), "Time"].to_list())
        
        # Number of self error
        self_error_count = len(tournament_results.loc[
            (((tournament_results["AgentA"] == agent_name) & (tournament_results["Who"] == "A"))
             | ((tournament_results["AgentB"] == agent_name) & (tournament_results["Who"] == "B")))
            & (tournament_results["Result"] == 'Error'),
            "Time"].to_list())

        # Number of self timed out
        self_timed_out_count = len(tournament_results.loc[
            (((tournament_results["AgentA"] == agent_name) & (tournament_results["Who"] == "A"))
             | ((tournament_results["AgentB"] == agent_name) & (tournament_results["Who"] == "B")))
            & (tournament_results["Result"] == 'TimedOut'),
            "Time"].to_list())

        acceptance_count = len(acceptance_times)
        total_negotiation = acceptance_count + failed_count + error_count + timed_out_count

        return {
            "AgentName": agent_name,
            "Avg.Utility": np.mean(utilities),
            "Median Utility": np.median(utilities),
            "Std.Utility": np.std(utilities),
            "Avg.OpponentUtility": np.mean(opponent_utilities),
            "Median OpponentUtility": np.median(opponent_utilities),
            "Std.OpponentUtility": np.std(opponent_utilities),
            "Avg.AcceptanceTime": np.mean(acceptance_times),
            "Median AcceptanceTime": np.median(acceptance_times),
            "Std.AcceptanceTime": np.std(acceptance_times),
            "Avg.Round": np.mean(rounds),
            "Median Round": np.median(rounds),
            "Std.Round": np.std(rounds),
            "Avg.ProductScore": np.mean(product_score),
            "Median ProductScore": np.median(product_score),
            "Std.ProductScore": np.std(product_score),
            "Avg.SocialWelfare": np.mean(social_welfare),
            "Median SocialWelfare": np.median(social_welfare),
            "Std.SocialWelfare": np.std(social_welfare),
            "Avg.NashDistance": np.mean(nash_distances),
            "Median NashDistance": np.median(nash_distances),
            "Std.NashDistance": np.std(nash_distances),
            "Avg.KalaiDistance": np.mean(kalai_distances),
            "Median KalaiDistance": np.median(kalai_distances),
            "Std.KalaiDistance": np.std(kalai_distances),
            "AcceptanceRate": acceptance_count / total_negotiation,
            "Count": total_negotiation,
            "Acceptance": acceptance_count,
            "Failed": failed_count,
            "Error": error_count,
            "TimedOut": timed_out_count,
            "SelfError": self_error_count,
            "SelfTimedOut": self_timed_out_count
        }
