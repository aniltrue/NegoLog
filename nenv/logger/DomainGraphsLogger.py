from nenv.logger.FinalGraphsLogger import FinalGraphsLogger, ExcelLog
from typing import List
import os


class DomainGraphsLogger(FinalGraphsLogger):
    """
        DomainGraphsLogger is a variant of FinalGraphsLogger. The difference is that DomainGraphsLogger draw the
        corresponding graphs domain-by-domain.
    """
    def on_tournament_end(self, tournament_logs: ExcelLog, agent_names: List[str], domain_names: List[str],
                          estimator_names: List[str]):

        if not os.path.exists(self.get_path("domains/")):
            os.makedirs(self.get_path("domains/"))

        tournament_results = tournament_logs.to_data_frame("TournamentResults")

        for domain_name in domain_names:
            domain_name = f"Domain{domain_name}"
            domain_dir = self.get_path("domains/%s/" % domain_name)

            if not os.path.exists(domain_dir):
                os.makedirs(domain_dir)

            domain_tournament_results = tournament_results.loc[tournament_results["DomainName"] == domain_name]

            self.draw_opponent_based(domain_tournament_results, agent_names, domain_dir)
