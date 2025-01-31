import datetime
import os
import random
import shutil
import time
import warnings
from typing import Union, Set, List, Tuple, Optional
import numpy as np
import pandas as pd
from nenv.Agent import AgentClass
from nenv.logger import AbstractLogger, LoggerClass
from nenv.OpponentModel import OpponentModelClass
from nenv.SessionManager import SessionManager
from nenv.utils import ExcelLog, TournamentProcessMonitor, open_folder


class Tournament:
    """
        This class conducts a tournament based on given settings.
    """
    agent_classes: Set[AgentClass]                 #: List of Agent classes
    loggers: List[AbstractLogger]                  #: List of Logger classes
    domains: List[str]                             #: List of domains
    estimators: Set[OpponentModelClass]            #: List of opponent models
    deadline_time: Optional[int]                    #: Time-based deadline in terms of seconds
    deadline_round: Optional[int]                   #: Round-based deadline in terms of number of rounds
    result_dir: str                                #: The directory where the result logs will be extracted
    seed: Optional[int]                             #: Random seed for whole tournament
    shuffle: bool                                  #: Whether the combinations will be shuffled, or not
    repeat: int                                    #: Number of repetition for each combination
    self_negotiation: bool                         #: Whether the agents negotiate with itself, or not
    tournament_process: TournamentProcessMonitor   #: Process monitor
    killed: bool                                   #: Whether the tournament process is killed, or not

    def __init__(self, agent_classes: Union[List[AgentClass], Set[AgentClass]],
                 domains: List[str],
                 logger_classes: Union[List[LoggerClass], Set[LoggerClass]],
                 estimator_classes: Union[List[OpponentModelClass], Set[OpponentModelClass]],
                 deadline_time: Optional[int],
                 deadline_round: Optional[int],
                 self_negotiation: bool = False,
                 repeat: int = 1,
                 result_dir: str = "results/",
                 seed: Optional[int] = None,
                 shuffle: bool = False
                 ):
        """
            This class conducts a negotiation tournament.

            :param agent_classes: List of agent classes (i.e., subclass of AbstractAgent class)
            :param domains: List of domains
            :param logger_classes: List of loggers classes (i.e., subclass of AbstractLogger class)
            :param estimator_classes: List of estimator classes (i.e, subclass of AbstractOpponentModel class)
            :param deadline_time: Time-based deadline in terms of seconds
            :param deadline_round: Round-based deadline in terms of number of rounds
            :param self_negotiation: Whether the agents negotiate with itself. *Default false*.
            :param repeat: Number of repetition for each combination. *Default 1*
            :param result_dir: The result directory that the tournament logs will be created. *Default 'results/'*
            :param seed: Setting seed for whole tournament. *Default None*.
            :param shuffle: Whether shuffle negotiation combinations. *Default False*
        """

        assert deadline_time is not None or deadline_round is not None, "No deadline type is specified."
        assert deadline_time is None or deadline_time > 0, "Deadline must be positive."
        assert deadline_round is None or deadline_round > 0, "Deadline must be positive."

        if repeat <= 0:
            warnings.warn("repeat is set to 1.")
            repeat = 1

        assert len(agent_classes) > 0, "Empty list of agent classes."
        assert len(domains) > 0, "Empty list of domains."

        self.agent_classes = agent_classes
        self.domains = domains
        self.estimators = estimator_classes
        self.deadline_time = deadline_time
        self.deadline_round = deadline_round
        self.loggers = [logger_class(result_dir) for logger_class in set(logger_classes)]
        self.result_dir = result_dir
        self.seed = seed
        self.repeat = repeat
        self.self_negotiation = self_negotiation
        self.shuffle = shuffle
        self.tournament_process = TournamentProcessMonitor()
        self.killed = False

    def run(self):
        """
            This method starts the tournament

            :return: Nothing
        """
        # Set seed
        if self.seed is not None:
            random.seed(self.seed)
            np.random.seed(self.seed)
            os.environ['PYTHONHASHSEED'] = str(self.seed)

        # Create directory
        if os.path.exists(self.result_dir):
            shutil.rmtree(self.result_dir)

        os.makedirs(self.result_dir)
        os.makedirs(os.path.join(os.path.join(self.result_dir, "sessions/")))

        # Set killed flag
        self.killed = False

        # Extract domain information into the result directory
        self.extract_domains()

        # Get all combinations
        negotiations = self.generate_combinations()

        # Names for logger
        agent_names = []
        estimator_names = []

        # Tournament log file
        tournament_logs = ExcelLog(["TournamentResults"])

        tournament_logs.save(os.path.join(self.result_dir, "results.xlsx"))

        self.tournament_process.initiate(len(negotiations))

        print(f'Started at {str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))}.')
        print("Total negotiation:", len(negotiations))

        print("*" * 50)

        for i, (agent_class_1, agent_class_2, domain_name) in enumerate(negotiations):
            # Start session
            session_runner = SessionManager(agent_class_1, agent_class_2, domain_name, self.deadline_time, self.deadline_round, list(self.estimators), self.loggers)

            session_path = "%s_%s_Domain%s.xlsx" % \
                           (session_runner.agentA.name, session_runner.agentB.name, domain_name)

            session_start_time = time.time()
            tournament_logs.append(session_runner.run(os.path.join(self.result_dir, "sessions/", session_path)))
            session_end_time = time.time()

            # Update total elapsed time
            session_elapsed_time = session_end_time - session_start_time

            tournament_logs.update({"TournamentResults": {"SessionRealTime": session_elapsed_time}})

            # Get list of name for loggers
            if len(estimator_names) == 0:
                estimator_names = [estimator.name for estimator in session_runner.agentA.estimators]

            if session_runner.agentA.name not in agent_names:
                agent_names.append(session_runner.agentA.name)

            if session_runner.agentB.name not in agent_names:
                agent_names.append(session_runner.agentB.name)

            print(self.tournament_process.update(f"{session_runner.agentA.name} vs. {session_runner.agentB.name } in Domain: {domain_name}", session_elapsed_time))

            if self.killed:  # Check for kill signal
                return

        self.tournament_process.end()
        print("*" * 50)
        print("Tournament has been done. Please, wait for analysis...")

        # Backup
        tournament_logs.save(os.path.join(self.result_dir, "results_backup.xlsx"))

        # On tournament end
        for logger in self.loggers:
            logger.on_tournament_end(tournament_logs, agent_names, self.domains, estimator_names)

        # Save tournament logs
        tournament_logs.save(os.path.join(self.result_dir, "results.xlsx"))

        print("Analysis have been completed.")
        print("*" * 50)

        print("Total Elapsed Time:", str(self.tournament_process.close()))

        # Show folder
        open_folder(self.result_dir)

    def generate_combinations(self) -> List[Tuple[AgentClass, AgentClass, str]]:
        """
            This method generates all combinations of negotiations.

            :return: Nothing
        """
        combinations = []

        for domain in self.domains:
            for agent_class_1 in self.agent_classes:
                for agent_class_2 in self.agent_classes:
                    if not self.self_negotiation and agent_class_1.__name__ == agent_class_2.__name__:
                        continue

                    for i in range(self.repeat):
                        combinations.append((agent_class_1, agent_class_2, domain))

        if self.shuffle:
            random.shuffle(combinations)

        return combinations

    def extract_domains(self):
        """
            This method extracts the domain information into the result directory.

            :return: Nothing
        """
        full_domains = pd.read_excel("domains/domains.xlsx", sheet_name="domains")

        domains = pd.DataFrame(columns=full_domains.columns[1:])

        domain_counter = 0

        for i, row in full_domains.iterrows():
            if str(row["DomainName"]) in self.domains:
                domains.loc[domain_counter] = row

                domain_counter += 1

        domains.to_excel(os.path.join(self.result_dir, "domains.xlsx"), sheet_name="domains", index=False)
