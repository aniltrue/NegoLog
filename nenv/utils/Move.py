"""
    Helpful functions for negotiation move processes.
"""
from typing import List, Dict

POSITIVE_MOVES = ["Fortunate", "Nice", "Concession"]
"""
    List of positive moves
"""

NEGATIVE_MOVES = ["Selfish", "Unfortunate", "Silent"]
"""
    List of negative moves
"""


def get_move(prev_offered_utility: float, offered_utility: float, prev_opponent_utility: float, opponent_utility: float, threshold: float = 0.03) -> str:
    """
        This method provides the corresponding move

        :param prev_offered_utility: The previous utility of the agent
        :param offered_utility: The current utility of the agent
        :param prev_opponent_utility: The previous utility of the opponent
        :param opponent_utility: The current utility of the opponent
        :param threshold: Threshold for *'Silent'* and *'Nice'* moves
        :return: The name of the move
    """
    diff_offered = offered_utility - prev_offered_utility
    diff_opponent = opponent_utility - prev_opponent_utility

    if abs(diff_offered) < threshold and abs(diff_opponent) < threshold:
        return "Silent"

    if abs(diff_offered) < threshold and diff_opponent > 0.:
        return "Nice"

    if diff_offered < 0 and diff_opponent >= 0:
        return "Concession"

    if diff_offered <= 0 and diff_opponent < 0:
        return "Unfortunate"

    if diff_offered > 0 and diff_opponent <= 0:
        return "Selfish"

    if diff_offered > 0 and diff_opponent > 0:
        return "Fortunate"

    return ""


def get_move_distribution(moves: List[str]) -> Dict[str, float]:
    """
        This method provides the move distribution

        :param moves: List of move names
        :return: Distribution as a dictionary
    """
    dist = {move: 0. for move in POSITIVE_MOVES}
    dist.update({move: 0. for move in NEGATIVE_MOVES})

    for move in moves:
        if move in dist.keys():
            dist[move] += 1

    total = sum(dist.values()) + 1e-8

    return {move: count / total for move, count in dist.items()}


def calculate_behavior_sensitivity(moves: List[str]) -> float:
    """
        This method calculates the behavior sensitivity

        :param moves: List of moves
        :return: Behavior sensitivity
    """
    count_positives = 0.
    count_negatives = 0.

    for move in moves:
        if move in POSITIVE_MOVES:
            count_positives += 1
        elif move in NEGATIVE_MOVES:
            count_negatives += 1

    return count_positives / (count_negatives + 1e-8)


def calculate_awareness(agent_moves: List[str], opponent_moves: List[str]) -> float:
    """
        This method calculates the awareness of the Agent B.

        If an agent has a higher awareness, it changes its move direction
        (i.e., from positive to negative, or vice versa) when the opponent changes.

        :param agent_moves: The list of the moves of the agent
        :param opponent_moves: The list of the moves of the opponent
        :return: Awareness
    """
    change_a_counter = 0.
    change_b_counter = 0.

    for i in range(1, min(len(agent_moves), len(opponent_moves))):
        if (agent_moves[i] in POSITIVE_MOVES and agent_moves[i - 1] in NEGATIVE_MOVES) or (agent_moves[i] in NEGATIVE_MOVES and agent_moves[i - 1] in POSITIVE_MOVES):
            change_a_counter += 1

            if (opponent_moves[i] in POSITIVE_MOVES and opponent_moves[i - 1] in NEGATIVE_MOVES) or (opponent_moves[i] in NEGATIVE_MOVES and opponent_moves[i - 1] in POSITIVE_MOVES):
                change_b_counter += 1

    return change_b_counter / (change_a_counter + 1e-8)


def calculate_move_correlation(agent_moves: List[str], opponent_moves: List[str]) -> float:
    """
        This method calculates the move direction correlation between the agent and the opponent.

        *Note:* Move direction correlation is calculated for the opponent.

        If an agent has a higher move direction correlation, it changes its move direction in the same way when its
        opponent changes.

        :param agent_moves: The list of the moves of the agent
        :param opponent_moves: The list of the moves of the opponent
        :return: Move direction correlation
    """
    change_agent_counter = 0.
    change_opponent_counter = 0.

    for i in range(1, min(len(agent_moves), len(opponent_moves))):
        if agent_moves[i] in POSITIVE_MOVES and agent_moves[i - 1] in NEGATIVE_MOVES:
            change_agent_counter += 1
            if opponent_moves[i] in POSITIVE_MOVES and opponent_moves[i - 1] in NEGATIVE_MOVES:
                change_opponent_counter += 1
            elif opponent_moves[i] in NEGATIVE_MOVES and opponent_moves[i - 1] in POSITIVE_MOVES:
                change_opponent_counter -= 1
        elif agent_moves[i] in NEGATIVE_MOVES and agent_moves[i - 1] in POSITIVE_MOVES:
            change_agent_counter += 1
            if opponent_moves[i] in NEGATIVE_MOVES and opponent_moves[i - 1] in POSITIVE_MOVES:
                change_opponent_counter += 1
            elif opponent_moves[i] in POSITIVE_MOVES and opponent_moves[i - 1] in NEGATIVE_MOVES:
                change_opponent_counter -= 1

    return change_opponent_counter / (change_agent_counter + 1e-8)
