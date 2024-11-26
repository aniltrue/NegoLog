"""
    This module contains some helpful methods and classes.
"""

from nenv.utils.ProcessManager import ProcessManager
from nenv.utils.SessionOps import AGENT_OPERATIONS, session_operation
from nenv.utils.KillableThread import KillableThread
from nenv.utils.ExcelLog import ExcelLog, LogRow
from nenv.utils.Move import get_move, get_move_distribution, calculate_move_correlation, calculate_awareness, calculate_behavior_sensitivity
from nenv.utils.tournament_graphs import DRAWING_FORMAT, set_drawing_format, draw_line, draw_heatmap
from nenv.utils.TournamentProcessMonitor import TournamentProcessMonitor
from nenv.utils.OSUtils import open_folder
