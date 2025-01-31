import math
from typing import List, Optional
import nenv
from agents.IAMhaggler.OpponentBid import OpponentHistory, OpponentBid
from agents.IAMhaggler.Regression import Regression


class IAMhaggler(nenv.AbstractAgent):
    """
        **IAMhaggler agent by Colin R. Williams**:
            IAMhaggler Agent predicts the negotiation time and utility when the opponent makes the highest concession.
            [Williams2012]_

        ANAC 2012 Nash category winner

        .. [Williams2012] Williams, C.R., Robu, V., Gerding, E.H., Jennings, N.R. (2012). IAMhaggler: A Negotiation Agent for Complex Environments. In: Ito, T., Zhang, M., Robu, V., Fatima, S., Matsuo, T. (eds) New Trends in Agent-Based Complex Automated Negotiations. Studies in Computational Intelligence, vol 383. Springer, Berlin, Heidelberg. <https://doi.org/10.1007/978-3-642-24696-8_10>
    """
    RISK_PARAMETER: float = 3.0                 #: Default value of Risk Factor
    regression: Regression                      #: Prediction model
    lastRegressionTime: float                   #: The last negotiation time when the prediction is made
    lastRegressionUtility: float                #: The last utility value when the prediction is made
    targetUtility: float                        #: Predicted target utility
    targetTime: float                           #: Predicted negotiation time
    history: OpponentHistory                    #: List of bids for prediction
    slotHistory: OpponentHistory                #: Last slot
    firstBidFromOpponent: Optional[nenv.Bid]    #: Fist received bid
    previousTargetUtility: float                #: Previous target utility that the agent calculated

    MAXIMUM_ASPIRATION: float = 0.9             #: For the acceptance strategy
    acceptMultiplier: float = 1.02              #: For the acceptance strategy
    lastTimeSlot = -1                           #: Number of time slots
    number_of_time_window: float                #: Number of time-window
    session_time: int                           #: Deadline

    def __init__(self, preference: nenv.Preference, session_time: int, estimators: List[nenv.OpponentModel.AbstractOpponentModel]):
        super().__init__(preference, session_time, estimators)

        self.session_time = session_time

    def initiate(self, opponent_name: Optional[str]):
        # Default values
        self.lastRegressionTime = 0.
        self.lastRegressionUtility = 1.
        self.targetTime = 1.
        self.targetUtility = 1.
        self.history = OpponentHistory()
        self.slotHistory = OpponentHistory()
        self.firstBidFromOpponent = None
        self.lastTimeSlot = -1
        self.regression = Regression()
        self.previousTargetUtility = -1

        # In the original paper, they defined the number of time-window as 36 due to tournament lasts 180 seconds.
        # We make it more dynamic, it is determined depending on the deadline.

        self.number_of_time_window = 36 * self.session_time / 180.
        # At least 5 time window.
        self.number_of_time_window = max(self.number_of_time_window, 5)

    @property
    def name(self) -> str:
        return "IAMhaggler"

    def receive_offer(self, bid: nenv.Bid, t: float):
        if self.firstBidFromOpponent is None:
            self.firstBidFromOpponent = bid

        # Append into the history
        self.slotHistory.history.append(OpponentBid(bid, t, self.preference))

    def act(self, t: float) -> nenv.Action:
        # In first rounds, offer the bid with the highest utility for me
        if not self.can_accept() or self.previousTargetUtility == -1:
            bid = self.preference.bids[0]
            self.previousTargetUtility = bid.utility

            return nenv.Offer(bid)

        # Apply acceptance strategy to decide accepting or not.
        if self.preference.get_utility(self.last_received_bids[-1]) * self.acceptMultiplier >= self.previousTargetUtility:
            return self.accept_action

        if self.preference.get_utility(self.last_received_bids[-1]) * self.acceptMultiplier >= self.MAXIMUM_ASPIRATION:
            return self.accept_action

        # Get target utility
        self.previousTargetUtility = self.get_target_utility(t)

        # Get a bid around the target utility
        bid = self.preference.get_random_bid(self.previousTargetUtility - 0.025, self.previousTargetUtility + 0.025)

        # Apply acceptance strategy for the new bid.
        if self.preference.get_utility(self.last_received_bids[-1]) * self.acceptMultiplier >= bid.utility:
            return self.accept_action

        # Offer the bid
        return nenv.Offer(bid)

    def get_target_utility(self, t: float):
        time_slot = math.floor(t * self.number_of_time_window)  # Time window

        if self.lastTimeSlot == -1:  # If the number of bids is not enough
            if len(self.slotHistory.history) > 0:
                self.history.history.append(self.slotHistory.get_maximum_bid())

                self.lastTimeSlot = time_slot

            # Time-Based strategy
            return 1. - t / 2

        if time_slot != self.lastTimeSlot and len(self.slotHistory.history) > 0:  # Time to training
            # Append
            self.history.history.append(self.slotHistory.get_maximum_bid())

            self.lastTimeSlot = time_slot

            if time_slot == 0:
                return 1. - t / 2.

            self.slotHistory = OpponentHistory()  # Clear the slot

            # Training and prediction
            intercept = self.firstBidFromOpponent.utility
            x, y = self.history.get_data(self.firstBidFromOpponent)

            self.targetTime, self.targetUtility = self.regression.fit_and_predict(x, y, intercept, self.RISK_PARAMETER, t)

            self.lastRegressionUtility = self.previousTargetUtility
            self.lastRegressionTime = t
        elif self.lastTimeSlot == 0 or time_slot == 0:
            # Time-Based strategy in the first rounds until there will be enough bids.
            return 1. - t / 2.

        # Calculate the current target utility
        target_utility = self.lastRegressionUtility + (t - self.lastRegressionTime) * \
                         (self.targetUtility - self.lastRegressionUtility) / \
                         (self.targetTime - self.lastRegressionTime)

        # Update time
        if t > self.targetTime:
            target_utility = self.targetUtility

        # Check for the reservation value
        target_utility = max(self.preference.reservation_value, target_utility)

        return target_utility
