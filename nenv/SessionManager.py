from typing import List, Union, Optional
from nenv.OpponentModel import OpponentModelClass
from nenv.Agent import AbstractAgent, AgentClass
from nenv.Session import Session
from nenv.Preference import Preference, domain_loader
from nenv.logger import AbstractLogger, LoggerClass
from nenv.utils import LogRow
from nenv.utils.ExcelLog import update


class SessionManager:
    """
        This class helps to run negotiation session.
    """
    prefA: Preference                #: Preferences of agentA
    prefB: Preference                #: Preferences of agentB
    loggers: List[AbstractLogger]    #: List of logger
    agentA: AbstractAgent            #: AgentA object
    agentB: AbstractAgent            #: AgentB object
    session: Session                 #: Negotiation session object
    deadline_time: Optional[int]    #: The time-based deadline in terms of seconds
    deadline_time: Optional[int]    #: The round-based in terms of number of rounds

    def __init__(self, agentA_class: AgentClass, agentB_class: AgentClass, domain_name: str, deadline_time: Optional[int], deadline_round: Optional[int], estimators: List[OpponentModelClass], loggers: List[LoggerClass]):
        """
            Constructor

            :param agentA_class: Class of AgentA, which is subclass of AbstractAgent class.
            :param agentB_class: Class of AgentB, which is subclass of AbstractAgent class.
            :param domain_name: The name of the domain
            :param deadline_time: Time-based deadline in terms of seconds
            :param deadline_round: Round-based deadline in terms of number of rounds
            :param estimators: List of Opponent Model
            :param loggers: List of logger
        """

        assert deadline_time is not None or deadline_round is not None, "No deadline type is specified."
        assert deadline_time is None or deadline_time > 0, "Deadline must be positive."
        assert deadline_round is None or deadline_round > 0, "Deadline must be positive."

        self.prefA, self.prefB = domain_loader(domain_name)
        self.domain_no = domain_name

        self.agentA = agentA_class(self.prefA, deadline_round if deadline_time is None else deadline_time, [estimator(self.prefA) for estimator in estimators])
        self.agentB = agentB_class(self.prefB, deadline_round if deadline_time is None else deadline_time, [estimator(self.prefB) for estimator in estimators])

        self.session = None
        self.deadline_time = deadline_time
        self.deadline_round = deadline_round
        self.loggers = loggers

    def run(self, save_path: str) -> LogRow:
        """
            Starts the negotiation session.

            :param save_path: Session log file
            :return: Log row for tournament
        """
        self.session = Session(self.agentA, self.agentB, save_path, self.deadline_time, self.deadline_round, self.loggers)

        session_result = self.session.start()

        # Update agents
        self.agentA = self.session.agentA
        self.agentB = self.session.agentB

        # Log some session information into tournament log
        session_result["TournamentResults"]["DomainName"] = self.domain_no
        session_result["TournamentResults"]["DomainSize"] = len(self.prefA.bids)
        session_result["TournamentResults"]["IssueSize"] = len(self.prefA.issues)
        session_result["TournamentResults"]["FilePath"] = save_path
        session_result["TournamentResults"]["DeadlineTime"] = self.deadline_time
        session_result["TournamentResults"]["DeadlineRound"] = self.deadline_round

        # On Session End logs
        for logger in self.loggers:
            update(session_result, logger.on_session_end(session_result, self.session))

        return session_result
