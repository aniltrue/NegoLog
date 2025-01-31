import math
from typing import Optional
import numpy as np
import nenv


class negotiatingInfo:
    pref: nenv.Preference
    issues: list
    opponents: list
    my_bid_history: Optional[list] = None
    bob_history: Optional[list] = None
    pb_list: Optional[list] = None

    opponents_bid_history: Optional[dict] = None
    opponents_average: dict
    opponents_variance: dict
    opponents_sum: dict
    opponents_pow_sum: dict
    opponents_stdev: dict
    value_relative_utility: Optional[dict] = None

    all_value_frequency: Optional[dict] = None
    opponents_value_frequency: Optional[dict] = None

    BOU:float
    MPBU: float
    time_scale: float
    round: int
    negotiator_num: int
    isLinerUtilitySpace: bool

    def __init__(self, preference: nenv.Preference):
        self.pref = preference
        self.issues = self.pref.issues.copy()
        self.BOU = 0.
        self.MPBU = 0.
        self.time_scale = 0.
        self.round = 0
        self.negotiator_num = 2
        self.isLinerUtilitySpace = True
        self.opponents = []
        self.my_bid_history = []
        self.bob_history = []
        self.pb_list = []
        self.opponents_bid_history = {}
        self.opponents_average = {}
        self.opponents_variance = {}
        self.opponents_sum = {}
        self.opponents_pow_sum = {}
        self.opponents_stdev = {}
        self.value_relative_utility = {}
        self.all_value_frequency = {}
        self.opponents_value_frequency = {}

        self.initAllValueFrequency()
        self.initValueRelativeUtility()

    def initOpponent(self, sender):
        self.initNegotiatingInfo(sender)

        self.initOpponentsValueFrequency(sender)

        self.opponents.append(sender)

    def updateInfo(self, sender, offeredBid: nenv.Bid):
        self.updateNegotiatingInfo(sender, offeredBid)

        self.updateFrequencyList(sender, offeredBid)

    def initNegotiatingInfo(self, sender):
        self.opponents_bid_history[sender] = []
        self.opponents_average[sender] = 0.
        self.opponents_variance[sender] = 0.
        self.opponents_sum[sender] = 0.
        self.opponents_pow_sum[sender] = 0.
        self.opponents_stdev[sender] = 0.

    def initOpponentsValueFrequency(self, sender):
        self.opponents_value_frequency[sender] = {}

        for issue in self.issues:
            self.opponents_value_frequency[sender][issue] = {}

            for value in issue.values:
                self.opponents_value_frequency[sender][issue][value] = 0.

    def initAllValueFrequency(self):
        for issue in self.issues:
            self.all_value_frequency[issue] = {}

            values = issue.values

            for value in values:
                self.all_value_frequency[issue][value] = 0.

    def initValueRelativeUtility(self):
        for issue in self.issues:
            self.value_relative_utility[issue] = {}

            values = issue.values

            for value in values:
                self.value_relative_utility[issue][value] = 0.

    def setValueRelativeUtility(self, maxBid: nenv.Bid):
        currentBid: nenv.Bid = None

        for issue in self.issues:
            currentBid = maxBid.copy()
            for value in issue.values:
                currentBid[issue] = value

                self.value_relative_utility[issue][value] = self.pref.get_utility(currentBid) - self.pref.get_utility(maxBid)

    def updateNegotiatingInfo(self, sender, offeredBid: nenv.Bid):
        self.opponents_bid_history[sender].append(offeredBid)

        util = self.pref.get_utility(offeredBid)

        self.opponents_sum[sender] += util
        self.opponents_pow_sum[sender] += math.pow(util, 2)

        round_num = len(self.opponents_bid_history[sender])
        self.opponents_average[sender] = self.opponents_sum[sender] / round_num
        self.opponents_variance[sender] = (self.opponents_pow_sum[sender] / round_num) - math.pow(self.opponents_average[sender], 2)
        if self.opponents_variance[sender] < 0:
            self.opponents_variance[sender] = 0.

        self.opponents_stdev[sender] = math.sqrt(self.opponents_variance[sender])

        if util > self.BOU:
            self.bob_history.append(offeredBid)
            self.BOU = util

    def updateFrequencyList(self, sender, offeredBid: nenv.Bid):
        for issue in self.issues:
            value = offeredBid[issue]

            self.opponents_value_frequency[sender][issue][value] = self.opponents_value_frequency[sender][issue][value] + 1
            self.all_value_frequency[issue][value] = self.all_value_frequency[issue][value] + 1

    def updateMyBidHistory(self, offeredBid: nenv.Bid):
        self.my_bid_history.append(offeredBid)

    def updateTimeScale(self, time: float):
        self.round += 1
        self.time_scale = time / self.round

    def updatePBList(self, popularBid: nenv.Bid):
        if popularBid not in self.pb_list:
            self.pb_list.append(popularBid)
            self.MPBU = max(self.MPBU, self.pref.get_utility(popularBid))
            self.pb_list = sorted(self.pb_list, key=lambda bid: self.pref.get_utility(bid), reverse=True)

    def getPartnerBidNum(self, sender):
        return len(self.opponents_bid_history[sender])

    def getValuebyFrequencyList(self, sender, issue: nenv.Issue):
        current_f = 0.
        max_f = 0.

        max_value = None

        randomOrderValues = issue.values.copy()
        np.random.shuffle(randomOrderValues)

        for value in randomOrderValues:
            current_f = self.opponents_value_frequency[sender][issue][value]

            if max_value is None or current_f > max_f:
                max_f = current_f
                max_value = value

        return max_value

    def getValueByAllFrequencyList(self, issue: nenv.Issue):
        current_f = 0.
        max_f = 0.

        max_value = None

        randomOrderValues = issue.values.copy()
        np.random.shuffle(randomOrderValues)

        for value in randomOrderValues:
            current_f = self.all_value_frequency[issue][value]

            if max_value is None or current_f > max_f:
                max_f = current_f
                max_value = value

        return max_value

    def utilitySpaceTypeisNonLiner(self):
        self.isLinerUtilitySpace = False
