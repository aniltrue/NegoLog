"""
    This module contains whole components of Opponent Model in Negotiation ENVironment.
"""

import typing

from nenv.OpponentModel.AbstractOpponentModel import AbstractOpponentModel

OpponentModelClass = typing.TypeVar('OpponentModelClass', bound=AbstractOpponentModel.__class__)
"""
    Type variable of AbstractOpponentModel class to declare a type for a variable
"""

from nenv.OpponentModel.EstimatedPreference import EstimatedPreference
from nenv.OpponentModel.ClassicFrequencyOpponentModel import ClassicFrequencyOpponentModel
from nenv.OpponentModel.WindowedFrequencyOpponentModel import WindowedFrequencyOpponentModel
from nenv.OpponentModel.BayesianOpponentModel import BayesianOpponentModel
from nenv.OpponentModel.ConflictBasedOpponentModel import ConflictBasedOpponentModel
