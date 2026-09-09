import datetime
import importlib
import inspect
import math
import os
from pathlib import Path
import random
import shutil
import time
import warnings
from typing import Union, Set, List, Tuple, Optional
from numbers import Integral, Real
import numpy as np
import pandas as pd
from nenv.Agent import AgentClass, AbstractAgent
from nenv.logger import AbstractLogger, LoggerClass
from nenv.OpponentModel import OpponentModelClass, AbstractOpponentModel
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

        if deadline_time is None and deadline_round is None:
            raise ValueError("At least one deadline must be specified.")
        if deadline_time is not None and (isinstance(deadline_time, bool) or not isinstance(deadline_time, Real)
                                          or not math.isfinite(deadline_time) or deadline_time <= 0):
            raise ValueError("deadline_time must be a finite positive number.")
        if deadline_round is not None and (isinstance(deadline_round, bool) or not isinstance(deadline_round, Integral)
                                           or deadline_round <= 0):
            raise ValueError("deadline_round must be a positive integer.")
        if isinstance(repeat, bool) or not isinstance(repeat, Integral):
            raise ValueError("repeat must be an integer.")
        if not isinstance(self_negotiation, bool) or not isinstance(shuffle, bool):
            raise ValueError("self_negotiation and shuffle must be booleans.")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, Integral) or not 0 <= seed < 2**32):
            raise ValueError("seed must be an integer from 0 through 2**32 - 1, or None.")
        self._validate_result_dir(result_dir)

        if repeat <= 0:
            warnings.warn("repeat is set to 1.")
            repeat = 1

        if not agent_classes or not domains or isinstance(domains, str):
            raise ValueError("Agents and domains must be nonempty collections.")
        if any(isinstance(domain, bool) or not isinstance(domain, (str, Integral))
               or not str(domain) or any(char in str(domain) for char in "/\\\0") for domain in domains):
            raise ValueError("Domain identifiers must be nonempty names without path separators.")

        def ordered_classes(classes, base_class):
            if isinstance(classes, (str, bytes)) or classes is None:
                raise TypeError("Components must be collections of concrete classes.")
            values = list(classes)
            if any(not inspect.isclass(value) or not issubclass(value, base_class)
                   or inspect.isabstract(value) for value in values):
                raise TypeError(f"Components must be concrete {base_class.__name__} subclasses.")
            if isinstance(classes, (set, frozenset)):
                return sorted(values, key=lambda cls: (cls.__module__, cls.__qualname__))
            return list(dict.fromkeys(values))

        self.agent_classes = ordered_classes(agent_classes, AbstractAgent)
        if len(self.agent_classes) < 2 and not self_negotiation:
            raise ValueError("Use at least two different agents or enable self_negotiation.")
        self.domains = [str(domain) for domain in domains]
        self.estimators = ordered_classes(estimator_classes, AbstractOpponentModel)
        self.deadline_time = deadline_time
        self.deadline_round = int(deadline_round) if deadline_round is not None else None
        self.loggers = [logger_class(result_dir) for logger_class in ordered_classes(logger_classes, AbstractLogger)]
        self.result_dir = result_dir
        self.seed = int(seed) if seed is not None else None
        self.repeat = int(repeat)
        self.self_negotiation = self_negotiation
        self.shuffle = shuffle
        self.tournament_process = TournamentProcessMonitor()
        self.killed = False
        self.cancelled = False
        self.failure = None
        self._tournament_logs = None

    @staticmethod
    def _validate_result_dir(result_dir):
        """Protect project inputs and ancestor directories from output replacement."""
        if not isinstance(result_dir, (str, os.PathLike)) or not str(result_dir).strip():
            raise ValueError("result_dir must be a nonempty directory path.")
        path = Path(result_dir)
        target = path.resolve()
        roots = {Path.cwd().resolve(), Path(__file__).resolve().parents[1]}
        protected = {root / name for root in roots for name in
                     ["agents", "nenv", "domains", "domain_generator", "web_framework", "docs", "docs-source",
                      "tests", ".git", ".github", "tournament_configurations", ".venv"]}
        if path.is_symlink() or any(target == root or target in root.parents for root in roots):
            raise ValueError("result_dir cannot replace the project or an ancestor directory.")
        if any(target == entry or entry in target.parents for entry in protected):
            raise ValueError("result_dir cannot replace project source, configuration or domain inputs.")
        if target.exists() and not target.is_dir():
            raise ValueError("result_dir must be a directory.")

    def run(self):
        """Run the tournament and record failure or cancellation consistently."""
        self.failure = None
        self.cancelled = False
        self._tournament_logs = None
        try:
            if self.killed:
                return
            self._run()
        except Exception as error:
            self.failure = str(error) or type(error).__name__
            if self._tournament_logs is not None:
                try:
                    self._tournament_logs.save(os.path.join(self.result_dir, "results.xlsx"))
                except Exception as save_error:
                    warnings.warn(f"Could not save interrupted tournament results: {save_error}")
            raise
        finally:
            if self.failure is not None or self.killed:
                self.cancelled = self.killed and self.failure is None
                self.tournament_process.is_active = False
                self.tournament_process.is_completed = False
                self.tournament_process.current_session = "Error" if self.failure else "Cancelled"
                self.tournament_process.last_update_time = time.time() if self.tournament_process.start_time else 0.
                self.tournament_process.last_update_datetime = datetime.datetime.now()

    def _run(self):
        """
            This method starts the tournament

            :return: Nothing
        """
        # Validate inputs before replacing an earlier result directory.
        self._validate_result_dir(self.result_dir)
        self._domain_metadata = pd.read_excel("domains/domains.xlsx", sheet_name="domains", dtype={"DomainName": str})
        if "DomainName" not in self._domain_metadata:
            raise ValueError("The domain catalog is missing DomainName.")
        missing_domains = set(self.domains) - set(self._domain_metadata["DomainName"].dropna())
        if missing_domains:
            raise ValueError("Domains missing from the catalog: " + ", ".join(sorted(missing_domains)))
        loader = importlib.import_module("nenv.SessionManager").domain_loader
        for domain in self.domains:
            if self.killed:
                return
            loader(domain)
        if self.killed:
            return

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

        # Extract domain information into the result directory
        self.extract_domains()

        # Get all combinations
        negotiations = self.generate_combinations()

        # Names for logger
        agent_names = []
        estimator_names = []

        # Tournament log file
        tournament_logs = ExcelLog(["TournamentResults"])
        self._tournament_logs = tournament_logs

        tournament_logs.save(os.path.join(self.result_dir, "results.xlsx"))

        self.tournament_process.initiate(len(negotiations))

        print(f'Started at {str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))}.')
        print("Total negotiation:", len(negotiations))

        print("*" * 50)

        session_counts = {}
        used_session_paths = set()
        for agent_class_1, agent_class_2, domain_name in negotiations:
            if self.killed:
                tournament_logs.save(os.path.join(self.result_dir, "results.xlsx"))
                return
            # Start session
            session_runner = SessionManager(agent_class_1, agent_class_2, domain_name, self.deadline_time, self.deadline_round, list(self.estimators), self.loggers)

            session_path = "%s_%s_Domain%s.xlsx" % \
                           (session_runner.agentA.name, session_runner.agentB.name, domain_name)
            base_path = session_path
            occurrence = session_counts.get(base_path, 0) + 1
            if occurrence > 1:
                session_path = base_path.removesuffix(".xlsx") + f"_repeat{occurrence}.xlsx"
            while session_path in used_session_paths:
                occurrence += 1
                session_path = base_path.removesuffix(".xlsx") + f"_repeat{occurrence}.xlsx"
            session_counts[base_path] = occurrence
            used_session_paths.add(session_path)

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
                tournament_logs.save(os.path.join(self.result_dir, "results.xlsx"))
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
                    if not self.self_negotiation and agent_class_1 is agent_class_2:
                        continue

                    for _ in range(self.repeat):
                        combinations.append((agent_class_1, agent_class_2, domain))

        if self.shuffle:
            random.shuffle(combinations)

        return combinations

    def extract_domains(self):
        """
            This method extracts the domain information into the result directory.

            :return: Nothing
        """
        full_domains = getattr(self, "_domain_metadata", None)
        if full_domains is None:
            full_domains = pd.read_excel("domains/domains.xlsx", sheet_name="domains", dtype={"DomainName": str})
        domains = full_domains[full_domains["DomainName"].isin(self.domains)]
        domains = domains.loc[:, ~domains.columns.str.startswith("Unnamed")]

        domains.to_excel(os.path.join(self.result_dir, "domains.xlsx"), sheet_name="domains", index=False)
