from typing import List
import ast

import nenv
from nenv.Action import Action
from nenv.Agent import AbstractAgent
from nenv.Bid import Bid
import json
from nenv.utils.ExcelLog import ExcelLog, LogRow, update


class SessionLogs:
    """
        SessionEstimator simulates the negotiation to generate additional logs after the tournament.
        It takes the previous session logs and simulates for the loggers.
    """
    agentA: AbstractAgent               #: AgentA object
    agentB: AbstractAgent               #: AgentB object
    session_log: ExcelLog               #: Session log
    loggers: list                       #: List of Loggers
    log_path: str                       #: Session Log csv path
    action_history: List[Action]        #: List of Action that the agents have taken
    round: int                         #: Round of the row currently being replayed

    def __init__(self, agentA: AbstractAgent, agentB: AbstractAgent, path: str, loggers: list, initiate_agents: bool = False):
        """
            Constructor

            :param agentA: AgentA object
            :param agentB: AgentB object
            :param path: Session log file path
            :param loggers: List of logger
            :param initiate_agents: Whether call *initiate* method of the agents, or not. *Default*: *False*
        """
        self.agentA = agentA

        self.agentB = agentB

        if initiate_agents:
            self.agentA.initiate("Opponent")
            self.agentB.initiate("Opponent")

        self.log_path = path

        self.loggers = loggers

        sheet_names = {"Session"}
        for estimator in self.agentA.estimators:
            sheet_names.add(estimator.name)

        self.action_history = []
        self.round = 0

        for logger in self.loggers:
            logger_sheet_names = logger.before_session_start(self)

            for sheet_name in logger_sheet_names:
                if sheet_name not in sheet_names:
                    sheet_names.add(sheet_name)

        self.session_log = ExcelLog(sheet_names, self.log_path)

    def parse_bid(self, bid_content: str) -> Bid:
        """
            This method converts string to Bid object

            :param bid_content: String
            :return: Bid object
        """

        if bid_content is None:
            return Bid({})

        # Current JSON and legacy Python dictionary representations both occur
        # in workbooks. Literal parsing preserves quotes without executing code.
        try:
            bid_dict = json.loads(bid_content)
        except json.JSONDecodeError:
            bid_dict = ast.literal_eval(bid_content)

        if not isinstance(bid_dict, dict):
            raise ValueError("BidContent must describe an issue-value dictionary.")

        return Bid(bid_dict)

    def process_row(self, row: dict, row_index: int, row_tournament: dict) -> dict:
        """
            This method simulates the round row in the session log

            :param row: Current log row
            :param row_index: Index of the row
            :param row_tournament: Tournament log row
            :return: Updated log row
        """
        self.round = int(row["Round"])
        bid = self.parse_bid(row["BidContent"])

        if row["Action"] == 'Accept':
            row_tournament["TournamentResults"]["Round"] = int(row["Round"])
            row_tournament["TournamentResults"]["Time"] = float(row["Time"])
            row_tournament["TournamentResults"]["NumOffer"] = len(self.action_history)
            row_tournament["TournamentResults"]["Who"] = row["Who"]
            row_tournament["TournamentResults"]["Result"] = 'Acceptance'
            row_tournament["TournamentResults"]["AgentAUtility"] = row["AgentAUtility"]
            row_tournament["TournamentResults"]["AgentBUtility"] = row["AgentBUtility"]
            row_tournament["TournamentResults"]["ProductScore"] = row["ProductScore"]
            row_tournament["TournamentResults"]["SocialWelfare"] = row["SocialWelfare"]
            row_tournament["TournamentResults"]["BidContent"] = row["BidContent"]

            self.action_history.append(nenv.Accept(bid))

            return row


        estimators = self.agentB.estimators if row["Who"] == 'A' else self.agentA.estimators

        t = float(row["Time"])

        self.action_history.append(Action(bid))

        # Update estimators
        for estimator in estimators:
            estimator.update(bid, t)

        # Update each sheet with loggers
        for logger in self.loggers:
            logger_row = logger.on_offer(row["Who"], bid, t, self)

            self.session_log.update(logger_row, row_index)

        return row

    def process_end(self, row: LogRow) -> LogRow:
        """
            This method is called when simulated session ends.

            :param row: Current tournament row
            :return: Updated tournament row
        """
        result = row["TournamentResults"]
        if result.get("Result") != "Acceptance":
            agent_a_utility = self.agentA.preference.reservation_value
            agent_b_utility = self.agentB.preference.reservation_value
            defaults = {
                "Round": len(self.action_history) // 2,
                "Time": 1.0,
                "NumOffer": len(self.action_history),
                "Who": "-",
                "Result": "Failed",
                "AgentAUtility": agent_a_utility,
                "AgentBUtility": agent_b_utility,
                "ProductScore": agent_a_utility * agent_b_utility,
                "SocialWelfare": agent_a_utility + agent_b_utility,
                "BidContent": None,
            }
            # The workbook cannot reconstruct agent errors or timeouts. Retain
            # the original outcome and fill only missing terminal fields.
            for key, value in defaults.items():
                result.setdefault(key, value)

        self.round = int(result["Round"])
        for logger in self.loggers:
            if result["Result"] == 'Acceptance':
                update(row, logger.on_accept(row["TournamentResults"]["Who"],
                                             self.parse_bid(row["TournamentResults"]["BidContent"]),
                                             float(row["TournamentResults"]["Time"]),
                                             self))
            else:
                update(row, logger.on_fail(float(row["TournamentResults"]["Time"]), self))

        return row

    def start(self, row_tournament: LogRow) -> LogRow:
        """
            This method simulates the all rounds for the estimators. Then, it updates the session log file.

            :return: LogRow of current session
        """
        for i, session_row in enumerate(self.session_log.log_rows["Session"]):
            self.process_row(session_row, i, row_tournament)

        # Save log
        self.session_log.save(self.log_path)

        self.process_end(row_tournament)

        # End session logs
        for logger in self.loggers:
            update(row_tournament, logger.on_session_end(row_tournament, self))

        return row_tournament
