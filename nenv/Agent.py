from typing import List, TypeVar, Union, Optional

import nenv
from nenv.Preference import Preference
from nenv.Bid import Bid
from nenv.Action import Action, Accept
from nenv.OpponentModel import AbstractOpponentModel
from abc import abstractmethod, ABC


class AbstractAgent(ABC):
    """
        Agents aim to reach a joint decision within a limited time through negotiation without fully revealing their
        preferences. During negotiation, agents must decide what to offer and when to accept the opponent's offer. To
        facilitate this process, this abstract class provides a framework for developing negotiating agents. Each agent
        must extend this abstract class to implement its specific negotiation strategy.

        **Components**:
            Negotiating agents can be formulated as consisting of three main components [BOAComponents]_.
                - **Bidding Strategy**:  Determines what to offer.
                - **Acceptance Strategy**: Decides when to accept the opponent's offer
                - **Opponent Model**: Estimates the preferences of the opponent.

            By extending this class, *bidding strategy* and *acceptance strategy* are implemented to develop an agent.
            To implement an opponent model, see also *AbstractOpponentModel* class.

        **Methods**:
            To extend this abstract class, following methods must be implemented.
                - **initiate**: Use this method to initialize required variables instead of the constructor.
                - **name**: Each agent must have a unique name for logging purposes.
                - **receive_offer**: This method is called when an offer is received. Generally, the opponent model can be updated in this method.
                - **act**: This method determines the action that the agent takes. It should include the *bidding strategy* and *acceptance strategy*.
                - **terminate**: This method is called at the end of the negotiation session.

        .. [BOAComponents] Tim Baarslag, Koen Hindriks, Mark Hendrikx, Alexander Dirkzwager, and Catholijn Jonker. 2014. Decoupling Negotiating Agents to Explore the Space of Negotiation Strategies. Springer Japan, Tokyo, 61–83. <https://doi.org/10.1007/978-4-431-54758-7_4>
    """
    preference: Preference                      #: Provided preferences for the agent
    last_received_bids: List[Bid]               #: The history of received bids from the opponent
    estimators: List[AbstractOpponentModel]     #: The list of Provided Opponent Model by the tournament settings
    session_time: int                           #: The maximum time (in terms of seconds) of the current session

    def __init__(self, preference: Preference, session_time: int, estimators: List[AbstractOpponentModel]):
        """
            Constructor of AbstractAgent class
            Agent must be a subclass of AbstractAgent. Each Agent implements necessary methods to run.

            :param preference: Agent's preference
            :param session_time: Maximum time (in terms of seconds) in that negotiation session.
            :param estimators: THe list of provided estimators.
        """
        self.preference = preference
        self.last_received_bids = []
        self.estimators = estimators
        self.session_time = session_time

    @property
    @abstractmethod
    def name(self) -> str:
        """
            Each agent must have a unique name for the loggers.

            :return: The name of Agent as string
        """
        pass

    @abstractmethod
    def initiate(self, opponent_name: Optional[str]):
        """
            This method is called before the negotiation session starts.
            You should initiate your agent in this method. Do not use constructor.

            :param opponent_name: Opponent name if learning is available, otherwise None
            :return: Nothing
        """
        pass

    def receive_bid(self, bid: Bid, t: float):
        """
            This method is called when a bid received from the opponent. This method add the received bid into the
            history. Then, it calls the receive_offer method.

            For the agent implementation, implement your strategy in **receive_offer** method instead of this method.

            :param bid: Received bid from the opponent
            :param t: Current negotiation time
            :return: Nothing
        """
        _bid = bid.copy_without_utility()
        _bid.utility = self.preference.get_utility(_bid)

        self.last_received_bids.append(_bid)

        for estimator in self.estimators:
            estimator.update(_bid, t)

        self.receive_offer(_bid, t)

    @abstractmethod
    def receive_offer(self, bid: Bid, t: float):
        """
            This method is called when a bid received from the opponent. Implement your strategy in this method.

            :param bid: Received bid from the opponent
            :param t: Current negotiation time
            :return: Nothing
        """
        pass

    @abstractmethod
    def act(self, t: float) -> Action:
        """
            This method is called by the negotiation session object to get the decision of the agent. The decision must
            be an Action object. The decision can be making offer or accepting the opponent's offer:\n
            - **Making offer**: You should return an **Offer** object such as: *nenv.Offer(bid)*
            - **Accepting offer**: You should return an **Accept** object such as *nevn.Accept(bid)*, or in a simpler manner: *self.accept_action*

            *Note* Do not forget to check whether the agent can accept the offer. Therefore, you can use **can_accept**
            method to check. Otherwise, your agent will be failed and penalized.

            :Example:
                This example belongs to time-based linear bidding strategy and AC_Next acceptance strategy.

                >>> target_utility = max(self.preference.reservation_value, t)  # Do not offer a bid with the utility lower than reservation value
                >>> bid = self.preference.get_bid_at(target_utility)    # Select the closest bid to the target utility
                >>> if self.can_accept() and bid <= self.last_received_bids[-1]:    # AC_Next acceptance strategy
                >>>     return self.accept_action   # Accept the opponent's offer
                >>>
                >>> return nenv.Offer(bid)  # Make an offer

            :param t: Current negotiation time
            :return: The decision of the agent as an Action object.
        """
        pass

    def terminate(self, is_accept: bool, opponent_name: str, t: float):
        """
            This method is called when the negotiation session end.

            :param is_accept: Whether the negotiation is end with an acceptance, or not
            :param opponent_name: The name of the opponent agent.
            :param t: Current negotiation time
            :return: Nothing
        """
        pass

    def can_accept(self) -> bool:
        """
            This method tells if the agent can accept the opponent's offer, or not.
            Please, call this method to check before accepting the offer.

            :return: Whether the agent can accept the opponent's offer, or not.
        """
        return len(self.last_received_bids) > 0

    @property
    def accept_action(self) -> Accept:
        """
            This method creates an Accept object in an easier manner.

            :return: Accept object to accept the opponent's offer.
        """
        return Accept(self.last_received_bids[-1])


AgentClass = TypeVar('AgentClass', bound=AbstractAgent.__class__)
"""
    Type variable of AbstractAgent class to declare a type for a variable
"""
