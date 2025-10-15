import time
from typing import List, Union, Optional
from nenv.Action import Accept, Action
from nenv.Agent import AbstractAgent
from nenv.BidSpace import BidSpace
from nenv.utils.ProcessManager import ProcessManager
from nenv.utils.SessionOps import session_operation
from nenv.utils.ExcelLog import ExcelLog, LogRow, update


class Session:
    """
        Session class holds the all necessary information about the negotiation session. It conducts the negotiation
        session by calling the corresponding methods.

        **Protocol**:
            The agents aim to reach a joint decision within a limited time through negotiation without fully revealing
            their preferences. The Session class enables the agent to engage in negotiation governed by a predefined
            protocol, specifically the *stacked alternating offer protocol*, a commonly used approach [Aydogan2017]_.
            AgentA initiates the negotiation by making the first offer. AgentB (the second agent) is presented with two
            options: propose a counter-offer or accept AgentA's offer. The turn then returns to AgentA, who can either
            accept the received offer or propose a counter-offer. This turn-taking process continues until an agreement
            is reached or the negotiation deadline expires. If no agreement is reached by the deadline, both parties
            receive zero utility or the reservation utility (if defined). This negotiation protocol ensures a structured
            and iterative exchange of offers, providing a systematic framework for the negotiation process.

            **Note**: The agents know only their own preferences.

        .. [Aydogan2017] Reyhan Aydoğan, David Festen, Koen V. Hindriks, and Catholijn M. Jonker. 2017. Alternating Offers Protocols for Multilateral Negotiation. Springer International Publishing, Cham, 153–167. <https://doi.org/10.1007/978-3-319-51563-2_10>
    """
    agentA: AbstractAgent                   #: AgentA object
    agentB: AbstractAgent                   #: AgentB object
    session_log: ExcelLog                   #: Session log
    loggers: list                           #: List of Loggers
    round: int                              #: Current negotiation round
    action_history: List[Action]            #: List of Action that the agents have taken
    bidSpace: BidSpace                      #: BidSpace object of the domain
    log_path: str                           #: Session Log csv path
    deadline_time: Optional[int]            #: Time-based deadline in terms of seconds
    deadline_round: Optional[int]           #: Round-based deadline in terms of seconds
    last_row: dict                          #: Last row of the log
    start_time: float                       #: Start time of the session
    process_manager: ProcessManager         #: Process Manager
    time_out: float                         #: Time out for any process

    def __init__(self, agentA: AbstractAgent, agentB: AbstractAgent, path: str, deadline_time: Optional[int], deadline_round: Optional[int], loggers: list):
        """
            Constructor

            :param agentA: AgentA object
            :param agentB: AgentB object
            :param path: Session log file path
            :param deadline_time: Time-Based deadline in terms of seconds.
            :param deadline_round: Round-based deadline in terms of number of rounds.
            :param loggers: List of logger
        """

        assert deadline_time is not None or deadline_round is not None, "No deadline type is specified."
        assert deadline_time is None or deadline_time > 0, "Deadline must be positive."
        assert deadline_round is None or deadline_round > 0, "Deadline must be positive."

        self.process_manager = ProcessManager()

        self.agentA = agentA
        self.agentB = agentB

        self.bidSpace = BidSpace(agentA.preference, agentB.preference)

        self.log_path = path
        self.deadline_time = deadline_time
        self.deadline_round = deadline_round
        self.last_row = {}
        self.action_history = []
        self.start_time = 0.
        self.round = 0
        self.time_out = min(600, deadline_time) if deadline_time is not None else 600

        sheet_names = {"Session"}

        for estimator in self.agentA.estimators:
            sheet_names.add(estimator.name)

        self.loggers = loggers

        for logger in self.loggers:
            logger_sheet_names = logger.before_session_start(self)

            for sheet_name in logger_sheet_names:
                sheet_names.add(sheet_name)

        self.session_log = ExcelLog(sheet_names)

    def get_time(self) -> float:
        """
            Get the normalized negotiation time.

            **Note**: If mixed deadline is set, the maximum normalized negotiation time will be provided.

            :return: Normalized negotiation time
        """

        if self.deadline_time is not None and self.deadline_round is not None:
            t_time = (time.time() - self.start_time) / self.deadline_time
            t_round = self.round / self.deadline_round

            return max(t_round, t_time)
        elif self.deadline_time is not None:
            return (time.time() - self.start_time) / self.deadline_time
        elif self.deadline_round is not None:
            return self.round / self.deadline_round
        else:
            raise Exception("No deadline is specified.")

    def on_offer(self, action: Action, agent_no: str, t: float):
        """
            This method is called when an offer received from an agent.

            :param action: Offer action
            :param agent_no: Who made the offer, *'A'* or *'B'*
            :param t: Negotiation time when received the offer
            :return: Log row for session
        """
        self.action_history.append(action)

        agent1_utility = self.agentA.preference.get_utility(action.bid)
        agent2_utility = self.agentB.preference.get_utility(action.bid)

        row = {
            "Round": self.round,
            "Time": t,
            "Who": agent_no,
            "Action": "Offer" if isinstance(action, Action) else "Accept",
            "AgentAUtility": agent1_utility,
            "AgentBUtility": agent2_utility,
            "ProductScore": agent1_utility * agent2_utility,
            "SocialWelfare": agent1_utility + agent2_utility,
            "BidContent": action.bid,
            "ElapsedTime": time.time() - self.start_time
        }

        self.session_log.append({"Session": row})

        # Update each sheet with loggers
        for logger in self.loggers:
            logger_row = logger.on_offer(agent_no, action.bid, t, self)

            self.session_log.update(logger_row)

        self.last_row = row

    def on_acceptance(self, agent_no: str, action: Accept, t: float) -> LogRow:
        """
            This method is called when an agent accepts.

            :param agent_no: Who accepted, *'A'* or *'B'*
            :param action: Accept action
            :param t: Acceptance time
            :return: Log row for tournament
        """
        self.action_history.append(action)

        agent1_utility = self.agentA.preference.get_utility(action.bid)
        agent2_utility = self.agentB.preference.get_utility(action.bid)

        row = {
            "Round": self.round,
            "Time": t,
            "Who": agent_no,
            "Action": "Accept",
            "AgentAUtility": agent1_utility,
            "AgentBUtility": agent2_utility,
            "ProductScore": agent1_utility * agent2_utility,
            "SocialWelfare": agent1_utility + agent2_utility,
            "BidContent": action.bid,
            "ElapsedTime": time.time() - self.start_time
        }

        self.session_log.append({"Session": row})

        self.session_log.save(self.log_path)

        # Terminate

        self._run_process_manager('A', 'Terminate', False, is_accept=True, opponent_name=self.agentB.name, t=t)
        self._run_process_manager('B', 'Terminate', False, is_accept=True, opponent_name=self.agentA.name, t=t)

        self.action_history.append(action)

        # Tournament log

        row = {"TournamentResults": {
            "AgentA": self.agentA.name,
            "AgentB": self.agentB.name,
            "Round": self.round,
            "Time": t,
            "NumOffer": self.get_number_of_offers(),
            "Who": agent_no,
            "Result": "Acceptance",
            "AgentAUtility": self.last_row["AgentAUtility"],
            "AgentBUtility": self.last_row["AgentBUtility"],
            "ProductScore": self.last_row["ProductScore"],
            "SocialWelfare": self.last_row["SocialWelfare"],
            "BidContent": action.bid,
            "ElapsedTime": time.time() - self.start_time
        }}

        for logger in self.loggers:
            update(row, logger.on_accept(agent_no, action.bid, t, self))

        return row

    def on_fail(self, t: float) -> LogRow:
        """
            This method is called when the deadline is up without any acceptance

            :param t: Negotiation time
            :return: Log row for tournament
        """
        self.session_log.save(self.log_path)

        # Terminate

        self._run_process_manager('A', 'Terminate', False, is_accept=False, opponent_name=self.agentB.name, t=t)
        self._run_process_manager('B', 'Terminate', False, is_accept=False, opponent_name=self.agentA.name, t=t)

        agentA_utility = self.agentA.preference.reservation_value
        agentB_utility = self.agentB.preference.reservation_value

        # Tournament Log

        row = {"TournamentResults": {
            "AgentA": self.agentA.name,
            "AgentB": self.agentB.name,
            "Round": self.round,
            "Time": t,
            "NumOffer": self.get_number_of_offers(),
            "Who": "-",
            "Result": "Failed",
            "AgentAUtility": agentA_utility,
            "AgentBUtility": agentB_utility,
            "ProductScore": agentA_utility * agentB_utility,
            "SocialWelfare": agentA_utility + agentB_utility,
            "BidContent": None,
            "ElapsedTime": time.time() - self.start_time
        }}

        for logger in self.loggers:
            update(row, logger.on_fail(t, self))

        return row

    def on_error(self, agent_no: str, t: float) -> LogRow:
        """
            This method is called when an error occurs. The agent which raises an error will get 0 utility.
            The other agent will get the reservation value.

            :param agent_no: The agent which raises an error.
            :param t: Negotiation time
            :return: Log row for tournament
        """
        self.session_log.save(self.log_path)

        # Terminate

        self._run_process_manager('A', 'Terminate', False, is_accept=False, opponent_name=self.agentB.name, t=t)
        self._run_process_manager('B', 'Terminate', False, is_accept=False, opponent_name=self.agentA.name, t=t)

        agentA_utility = 0.0 if agent_no == 'A' else self.agentA.preference.reservation_value
        agentB_utility = 0.0 if agent_no == 'B' else self.agentB.preference.reservation_value

        # Tournament log

        row = {"TournamentResults": {
            "AgentA": self.agentA.name,
            "AgentB": self.agentB.name,
            "Round": self.round,
            "Time": t,
            "NumOffer": self.get_number_of_offers(),
            "Who": agent_no,
            "Result": "Error",
            "AgentAUtility": agentA_utility,
            "AgentBUtility": agentB_utility,
            "ProductScore": agentA_utility * agentB_utility,
            "SocialWelfare": agentA_utility + agentB_utility,
            "BidContent": None,
            "ElapsedTime": time.time() - self.start_time
        }}

        for logger in self.loggers:
            update(row, logger.on_fail(t, self))

        return row

    def on_timed_out(self, agent_no: str, t: float) -> LogRow:
        """
            This method is called when a process of the agent is timed out. The agent which raises an error will get 0
            utility. The other agent will get the reservation value.

            :param agent_no: The agent which has timed out process
            :param t: Negotiation time
            :return: Log row for tournament
        """
        self.session_log.save(self.log_path)

        # Terminate

        self._run_process_manager('A', 'Terminate', False, is_accept=False, opponent_name=self.agentB.name, t=t)
        self._run_process_manager('B', 'Terminate', False, is_accept=False, opponent_name=self.agentA.name, t=t)

        agentA_utility = 0.0 if agent_no == 'A' else self.agentA.preference.reservation_value
        agentB_utility = 0.0 if agent_no == 'B' else self.agentB.preference.reservation_value

        # Tournament log

        row = {"TournamentResults": {
            "AgentA": self.agentA.name,
            "AgentB": self.agentB.name,
            "Round": self.round,
            "Time": t,
            "NumOffer": self.get_number_of_offers(),
            "Who": agent_no,
            "Result": "TimedOut",
            "AgentAUtility": agentA_utility,
            "AgentBUtility": agentB_utility,
            "ProductScore": agentA_utility * agentB_utility,
            "SocialWelfare": agentA_utility + agentB_utility,
            "BidContent": None,
            "ElapsedTime": time.time() - self.start_time
        }}

        for logger in self.loggers:
            update(row, logger.on_fail(t, self))

        return row

    def _run_process_manager(self, agent_no: str, process_name: str, call_events: bool = True, **kwargs) -> \
            Union[dict, Action, None]:
        """
            This method calls the corresponding process with the process manager. If any exception is occurred,
            or the initiation process is timed out, this method returns a corresponding tournament log to end the
            negotiation session. Otherwise, it provides the return value of the process.

            :param agent_no: Agent no
            :param process_name: Process name
            :param call_events: If calling on_error or on_timed_out methods, or not
            :param kwargs: Required arguments
            :return: Return value of the process, or corresponding tournament log to end the negotiation
        """

        kwargs["agent"] = self.agentA if agent_no == 'A' else self.agentB
        kwargs["process_name"] = process_name

        self.process_manager.run(session_operation, self.time_out, kwargs)

        if self.process_manager.has_exception:
            print(
                f"Exception occurs in {self.agentA.name if agent_no == 'A' else self.agentB.name} while {process_name}:")
            print(self.process_manager.exception)

            if call_events:
                return self.on_error(agent_no, kwargs.get('t', 0))
            else:
                return {}
        elif self.process_manager.time_outed:
            print(f"Timed Out: {self.agentA.name if agent_no == 'A' else self.agentB.name} while {process_name}")

            if call_events:
                return self.on_timed_out(agent_no, kwargs.get('t', 0))
            else:
                return {}
        else:
            return self.process_manager.return_val

    def start(self) -> LogRow:
        """
            This method starts the negotiation.

            :return: Log row for tournament
        """

        # print(f"{self.agentA.name} vs. {self.agentB.name} is started.")

        # Initiate agentA
        initiating_result = self._run_process_manager('A', 'Initiate', opponent_name=self.agentB.name)

        if initiating_result:  # If any problem occurs, end the session
            return initiating_result

        # Initiate agentA
        initiating_result = self._run_process_manager('B', 'Initiate', opponent_name=self.agentA.name)

        if initiating_result:  # If any problem occurs, end the session
            return initiating_result

        action = None
        self.round = 0
        self.start_time = time.time()
        t = self.get_time()

        while t < 1.:  # Until deadline
            # AgentA
            if self.round > 0:
                receiving_bid_result = self._run_process_manager('A', 'Receive Bid', bid=action.bid, t=t)

                if receiving_bid_result:  # If any problem occurs, end the session
                    return receiving_bid_result

            act_result = self._run_process_manager('A', 'Act', t=t)

            if isinstance(act_result, dict):  # If any problem occurs, end the session
                return act_result
            else:
                action = act_result

            if action is None or not isinstance(action, Action):
                return self.on_error("A", t)

            if isinstance(action, Accept) and self.round == 0:  # Forbidden action
                return self.on_error("A", t)
            if isinstance(action, Accept):
                return self.on_acceptance("A", action, t)
            else:
                self.on_offer(action, "A", t)

            # time.sleep(random.random() * 0.09 + 0.01)

            t = self.get_time()

            if t >= 1.:
                return self.on_fail(t)

            # AgentB
            receiving_bid_result = self._run_process_manager('B', 'Receive Bid', bid=action.bid, t=t)

            if receiving_bid_result:  # If any problem occurs, end the session
                return receiving_bid_result

            act_result = self._run_process_manager('B', 'Act', t=t)

            if isinstance(act_result, dict):  # If any problem occurs, end the session
                return act_result
            else:
                action = act_result

            if action is None or not isinstance(action, Action):
                return self.on_error("B", t)

            if isinstance(action, Accept):
                return self.on_acceptance("B", action, t)
            else:
                self.on_offer(action, "B", t)

            self.round += 1
            t = self.get_time()

            # time.sleep(random.random() * 0.09 + 0.01)

        return self.on_fail(t)

    def get_number_of_offers(self) -> int:
        """
            This method provides the number of offered bid.

            :return: Number of offers
        """
        counter = 0

        for action in self.action_history:
            if not isinstance(action, Accept):
                counter += 1

        return counter
