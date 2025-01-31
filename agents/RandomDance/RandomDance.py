import math
import random
from typing import Dict, List, Set, Optional
import nenv
from nenv import Action, Bid


class IssueData:
    locked: bool
    weight: float
    derta: float
    max: float
    map: Dict[str, float]
    adder: float
    issue: nenv.Issue
    values: List[str]

    def __init__(self, issue: nenv.Issue, derta: float):
        self.issue = issue
        self.derta = derta
        self.locked = False
        self.weight = 1.
        self.max = 1.
        self.map = {value: 0. for value in self.issue.values}
        self.adder = 1.
        self.values = self.issue.values

    def Locked(self):
        self.locked = True

    def isLocked(self):
        return self.locked

    def GetValue(self, value: str):
        return self.map[value] / self.max

    def GetValueWithWeight(self, value: str):
        return self.GetValue(value) * self.weight

    def Update(self, value: str):
        self.map[value] = self.map.get(value) + self.adder
        self.max = max(self.max, self.map[value])
        self.adder *= self.derta

    def setValue(self, value: str, util: float):
        if not self.isLocked():
            self.map[value] = util


class PlayerData:
    map: Dict[nenv.Issue, IssueData]
    history: Set[nenv.Bid]
    derta = float

    def __init__(self, issues: list, derta: float):
        self.map = {}
        self.history = set()
        self.derta = derta

        for issue in issues:
            self.map[issue] = IssueData(issue, derta)

    def GetUtility(self, bid: nenv.Bid):
        ret = 0.

        for issue, value in bid:
            ret += self.map[issue].GetValueWithWeight(value)

        return ret

    def SetMyUtility(self, pref: nenv.Preference):
        bid = pref.bids[-1]
        issues = pref.issues
        min = pref.get_utility(bid)

        for issue in issues:
            issueData = self.map[issue]
            bid = pref.bids[-1]
            values = issueData.values

            for value in values:
                bid[issue] = value
                v = pref.get_utility(bid) - min
                issueData.setValue(value, v)

            issueData.weight = 1. / (1. - min)
            issueData.Locked()

    def AddBid(self, bid: nenv.Bid):
        if bid in self.history:
            return

        self.history.add(bid)

        countsum = 0

        for issue in bid.content.keys():
            self.map[issue].Update(bid[issue])
            countsum += self.map[issue].max

        for issue in bid.content.keys():
            self.map[issue].weight = self.map[issue].max / countsum


class PlayerDataLib:
    playerDatas = List[PlayerData]

    def __init__(self, issues: list):
        self.playerDatas = []
        self.playerDatas.append(PlayerData(issues, 1.))
        self.playerDatas.append(PlayerData(issues, 1.05))
        self.playerDatas.append(PlayerData(issues, 0.55))

    def getRandomPlayerData(self) -> PlayerData:
        return random.choice(self.playerDatas)

    def AddBid(self, bid: nenv.Bid):
        for playerData in self.playerDatas:
            playerData.AddBid(bid)


class RandomDance(nenv.AbstractAgent):
    """
        **RandomDance agent by Shinji Kakimoto**:
            In multi-lateral negotiations, agents need to simultaneously estimate the utility functions of more than two
            agents. RandomDance agent proposes an estimating method that uses simple weighted functions by counting the
            opponent’s evaluation value for each issue. For multi-lateral negotiations, RandomDance agent considers some
            utility functions as the `single` utility function by weighted-summing them. RandomDance agent needs to
            judge which weighted function is effective and the types of the opponents. However, they depend on the
            domains, agents’ strategies and so on. RandomDance agent selects the weighted function and opponent’s
            weighting, randomly. [Kakimoto2017]_

        ANAC 2015 individual utility category finalist.

        .. [Kakimoto2017] Kakimoto, S., Fujita, K. (2017). RandomDance: Compromising Strategy Considering Interdependencies of Issues with Randomness. In: Fujita, K., et al. Modern Approaches to Agent-based Complex Automated Negotiation. Studies in Computational Intelligence, vol 674. Springer, Cham. <https://doi.org/10.1007/978-3-319-51563-2_13>
    """
    NashCountMax: int
    NumberOfAcceptSafety: int
    NumberOfRandomTargetCheck: int
    utilityDatas = Dict[str, PlayerDataLib]
    myData: PlayerData
    nash: List[str]
    olderBidMap: Dict[str, nenv.Bid]
    olderBid: Optional[nenv.Bid]

    discountFactor: float
    reservationValue: float

    olderTime: float

    @property
    def name(self) -> str:
        return "RandomDance"

    def initiate(self, opponent_name: Optional[str]):
        self.NashCountMax = 200
        self.NumberOfAcceptSafety = 5
        self.NumberOfRandomTargetCheck = 3
        self.utilityDatas = {}
        self.myData = PlayerData(self.preference.issues, 1.)
        self.myData.SetMyUtility(self.preference)
        self.nash = []
        self.olderBidMap = {}
        self.olderBid = None
        self.discountFactor = 1.
        self.reservationValue = self.preference.reservation_value
        self.olderTime = 0.

    def receive_offer(self, bid: Bid, t: float):
        sender = "OpponentAgent"

        if sender not in self.utilityDatas.keys():
            self.utilityDatas[sender] = PlayerDataLib(self.preference.issues)

        self.olderBid = bid.copy()

        self.olderBidMap[sender] = self.olderBid

        self.utilityDatas[sender].AddBid(self.olderBid)

    def act(self, t: float) -> Action:
        utilityMap = {s: self.utilityDatas[s].getRandomPlayerData() for s in self.utilityDatas.keys()}
        utilityMap["my"] = self.myData

        maxval: float = -999
        maxPlayer: Optional[str] = None

        for string in self.olderBidMap.keys():
            utility = 1.

            for player in utilityMap.keys():
                if string == player:
                    continue

                utility *= utilityMap[player].GetUtility(self.olderBidMap[string])

            if utility > maxval:
                maxval = utility
                maxPlayer = string

        if maxPlayer is not None:
            self.nash.append(maxPlayer)

        while len(self.nash) > self.NashCountMax:
            self.nash.pop(0)

        playerWeight = self.getWeights()

        action: Optional[nenv.Action] = None
        offer: Optional[nenv.Action] = None

        target = self.GetTarget(utilityMap, t)
        utility = 0

        if self.olderBid is not None:
            utility = self.preference.get_utility(self.olderBid)

        offer = nenv.Offer(self.SearchBid(target, utilityMap, playerWeight))
        action = offer

        if action is None or self.IsAccept(target, utility, t):
            return self.accept_action

        return action

    def getWeights(self):
        playerWeight = {}

        rand = int(random.random() * 3)

        if rand == 0:
            for string in self.utilityDatas.keys():
                playerWeight[string] = 0.0001

            for string in self.nash:
                playerWeight[string] += 1
        elif rand == 1:
            for string in self.utilityDatas.keys():
                playerWeight[string] = 1.
        elif rand == 2:
            flag = random.random() < 0.5

            for string in self.utilityDatas.keys():
                if string == "my":
                    continue

                if flag:
                    playerWeight[string] = 1.
                else:
                    playerWeight[string] = 0.01

                flag = not flag
        else:
            for string in self.utilityDatas.keys():
                playerWeight[string] = 1.0

        return playerWeight

    def IsAccept(self, target: float, utility: float, time: float):
        d = time - self.olderTime
        self.olderTime = time

        if not self.can_accept():
            return False

        if time + d * self.NumberOfAcceptSafety > 1.:
            return True

        if self.olderBid is None:
            return False

        if utility > target:
            return True

        return False

    def GetTarget(self, datas: dict, t: float):
        m = 0

        weights = {}

        for i in range(self.NumberOfRandomTargetCheck):
            utilityMap = {}

            for str in self.utilityDatas.keys():
                utilityMap[str] = self.utilityDatas[str].getRandomPlayerData()
                weights[str] = 1.

            utilityMap["my"] = self.myData
            weights["my"] = 1.

            bid = self.SearchBidWithWeights(utilityMap, weights)

            m = max(m, self.preference.get_utility(bid))

        target = 1. - (1 - m) * math.pow(t, self.discountFactor)

        if self.discountFactor > 0.99:
            target = 1. - (1. - m) * math.pow(t, 3)

        return target

    def SearchBidWithWeights(self, datas: dict, weights: dict):
        ret = self.preference.get_random_bid().copy()

        for issue in self.preference.issues:
            values = issue.values

            m = -1
            maxValue = None

            for value in values:
                v = 0.

                for string in datas.keys():
                    data = datas[string]
                    weight = weights[string]
                    v += data.map[issue].GetValueWithWeight(value) * weight

                if v > m:
                    m = v
                    maxValue = value

            if maxValue is not None:
                ret[issue] = maxValue

        return ret

    def SearchBid(self, target: float, datas: dict, weights: dict):
        map = {key: value for key, value in datas.items()}
        map["my"] = self.myData

        s = sum(weights.values())

        weightbuf = {key: value / s for key, value in weights.items()}

        w = 0.
        while w < 9.999:
            myweight = w / (1. - w)
            weightbuf["my"] = myweight
            bid = self.SearchBidWithWeights(map, weightbuf)
            if self.preference.get_utility(bid) > target:
                return bid

            w += 0.01

        return self.preference.bids[0]
