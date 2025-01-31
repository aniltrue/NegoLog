import math
import random
from typing import Dict, List, Optional
import nenv


class BidUtility:
    bid: nenv.Bid
    utility: float
    time: float

    def __init__(self, bid: nenv.Bid, u: float, t: float):
        self.bid = bid
        self.utility = u
        self.time = t

    def copy(self):
        return BidUtility(self.bid.copy(), self.utility, self.time)


class OpponentPreferences:
    repeatedIssue: Dict[nenv.Issue, Dict[str, int]]
    selectedValues: list
    opponentBids: List[BidUtility]

    def __init__(self):
        self.repeatedIssue = {}
        self.selectedValues = []
        self.opponentBids = []


class ParsAgent(nenv.AbstractAgent):
    """
        **Pars agent by Zahra Khosravimehr**:
            Pars agent uses a hybrid bidding strategy that combines behaviors of time-dependent, random and
            frequency-based strategies to propose a high utility offer close to the opponents bids and to increase the
            possibility of early agreement. [Khosravimehr2017]_

        ANAC 2015 individual utility category finalist.

        .. [Khosravimehr2017] Khosravimehr, Z., Nassiri-Mofakham, F. (2017). Pars Agent: Hybrid Time-Dependent, Random and Frequency-Based Bidding and Acceptance Strategies in Multilateral Negotiations. In: Fujita, K., et al. Modern Approaches to Agent-based Complex Automated Negotiation. Studies in Computational Intelligence, vol 674. Springer, Cham. <https://doi.org/10.1007/978-3-319-51563-2_12>
    """
    lastBid: Optional[nenv.Bid]
    lastAction: nenv.Action
    oppAName: Optional[str]
    oppBName: str
    round_: int
    myutility: float
    Imfirst: bool
    withDiscount: Optional[bool]
    fornullAgent: bool
    opponentAB: List[BidUtility]
    oppAPreferences: OpponentPreferences
    oppBPreferences: OpponentPreferences

    def initiate(self, opponent_name: Optional[str]):
        self.myutility = 0.8
        self.Imfirst = False
        self.withDiscount = None
        self.fornullAgent = False
        self.opponentAB = []
        self.oppAPreferences = OpponentPreferences()
        self.oppBPreferences = OpponentPreferences()
        self.lastBid = None
        self.oppAName = None

    @property
    def name(self) -> str:
        return "ParsAgent"

    def act(self, t: float) -> nenv.Action:
        if self.lastBid is None:
            self.Imfirst = True

            return nenv.Offer(self.getMyBestBid(self.preference.bids[0], 0.))

        if self.can_accept() and self.preference.get_utility(self.lastBid) > self.getMyUtility(t):
            return self.accept_action

        b = self.offerMyNewBid(t)

        if self.preference.get_utility(b) < self.getMyUtility(t):
            return nenv.Offer(self.getMyBestBid(self.preference.bids[0], 0))

        return nenv.Offer(b)

    def receive_offer(self, bid: nenv.Bid, t: float):
        agentName = "OpponentAgent"

        self.fornullAgent = not self.fornullAgent

        if self.withDiscount is not None:
            self.withDiscount = False

        opBid = BidUtility(bid.copy(), self.preference.get_utility(bid), t)

        if self.oppAName is None:
            self.oppAName = agentName
            self.oppAPreferences.opponentBids.append(opBid)
        else:
            self.addBidToList(self.oppAPreferences.opponentBids, opBid)

        self.calculateParamForOpponent(self.oppAPreferences, bid)
        self.lastBid = bid

    def MyBestValue(self, issue: nenv.Issue):
        values = [[value, weight] for value, weight in self.preference.value_weights[issue].items()]

        bestValue = max(values, key=lambda x: x[1])[0]

        return bestValue

    def offerMyNewBid(self, t: float):
        bidNN: Optional[nenv.Bid] = None

        if len(self.opponentAB) > 0:
            bidNN = self.getNNBid(self.opponentAB, t)

        if bidNN is not None and self.preference.get_utility(bidNN) >= self.getMyUtility(t):
            return bidNN

        issues = self.getMutualIssues()
        map = {}
        bid: Optional[nenv.Bid] = None

        dissues = self.preference.issues

        for i in range(len(dissues)):
            keyVal = issues[i]

            dissue = dissues[i]

            if keyVal is not None:
                for num in range(len(dissue.values)):
                    if dissue.values[num] == keyVal[0]:
                        map[dissue] = dissue.values[num]
                        break
            else:
                map[dissue] = self.MyBestValue(dissue)

        bid = nenv.Bid(map)

        if self.preference.get_utility(bid) > self.getMyUtility(t):
            return bid

        return self.getMyBestBid(self.preference.bids[0], 0)

    def getMutualIssues(self):
        mutualList = []
        dissues = self.preference.issues
        twocycle = 2

        while twocycle > 0:
            mutualList = []

            for i in range(len(dissues)):
                self.updateMutualList(mutualList, dissues, twocycle, i)

                if len(self.oppAPreferences.repeatedIssue[dissues[i]]) == 0 or (self.oppBPreferences is not None and len(self.oppBPreferences.repeatedIssue[dissues[i]]) == 0):
                    twocycle -= 1

            if twocycle != 0:
                twocycle -= 1

                if len(self.opponentAB) == 0:
                    nullval = 0.

                    for i in range(len(mutualList)):
                        if mutualList[i] is not None:
                            nullval += 1

                    nullval /= len(mutualList)

                    if nullval >= 0.5:
                        twocycle -= 1
                else:
                    twocycle -= 1

        return mutualList

    def updateMutualList(self, mutualList: list, dissues: list, twocycle: int, i: int):
        if dissues[i] in self.oppAPreferences.repeatedIssue.keys():
            vals = self.oppAPreferences.repeatedIssue[dissues[i]]
            valsB = self.oppBPreferences.repeatedIssue.get(dissues[i], None)

            keys = list(vals.keys())

            max = [0, 0]

            maxkey = [None, None]

            for j in range(len(keys)):
                temp = vals[keys[j]]

                if temp > max[0]:
                    max[0] = temp
                    maxkey[0] = keys[j]
                elif temp > max[1]:
                    max[1] = temp
                    maxkey[1] = keys[j]

            if valsB is not None:
                keysB = list(valsB.keys())

                maxB = [0, 0]

                maxkeyB = [None, None]

                for j in range(len(keysB)):
                    temp = valsB[keysB[j]]

                    if temp > maxB[0]:
                        maxB[0] = temp
                        maxkeyB[0] = keysB[j]
                    elif temp > maxB[1]:
                        maxB[1] = temp
                        maxkeyB[1] = keysB[j]

                if twocycle == 2:
                    if maxkey[0] is not None and maxkeyB[0] is not None and maxkey[0] == maxkeyB[0]:
                        mutualList.insert(i, [maxkey[0], maxB[0], max[0]])
                    else:
                        mutualList.insert(i, None)
                else:
                    insideloop = True

                    for m in range(2):
                        if not insideloop:
                            break

                        for z in range(2):
                            if maxkey[m] is not None and maxkeyB[z] is not None and maxkey[m] == maxkeyB[z]:
                                mutualList.insert(i, [maxkey[0], maxB[0], max[0]])
                                insideloop = False
                                break

                    if insideloop:
                        mutualList.insert(i, None)
            else:
                mutualList.insert(i, None)
                self.oppBPreferences.repeatedIssue[dissues[i]] = {}
        else:
            self.oppAPreferences.repeatedIssue[dissues[i]] = {}
            mutualList.insert(i, None)

    def getNNBid(self, oppAB: list, t: float):
        dissues = self.preference.issues
        maxBid = None
        maxutility = 0.
        size = 0
        exloop = 0
        newBid: nenv.Bid

        while exloop < len(dissues):
            bi = self.chooseBestIssue()

            size = 0

            while oppAB is not None and len(oppAB) > size:
                b = oppAB[size].bid
                newBid = b.copy()

                vals = b.content

                vals[dissues[bi]] = self.getRandomValue(dissues[bi])
                newBid = nenv.Bid(vals)

                if self.preference.get_utility(newBid) > self.getMyUtility(t) and self.preference.get_utility(newBid) > maxutility:
                    maxBid = newBid.copy()
                    maxutility = self.preference.get_utility(maxBid)

                size += 1

            exloop += 1

        return maxBid

    def chooseBestIssue(self):
        rnd = random.random()
        sumWeight = 0.

        for i in reversed(range(len(self.preference.issues))):
            sumWeight += self.preference.issue_weights[self.preference.issues[i]]

            if sumWeight > rnd:
                return i

        return 0

    def chooseWorstIssue(self):
        rnd = random.random() * 100
        sumWeight = 0.
        minin = 1
        min = 1.

        for i in reversed(range(len(self.preference.issues))):
            sumWeight += 1. / self.preference.issue_weights[self.preference.issues[i]]

            if self.preference.issue_weights[self.preference.issues[i]] < min:
                min = self.preference.issue_weights[self.preference.issues[i]]
                minin = i

            if sumWeight > rnd:
                return i

        return minin

    def getMyBestBid(self, sugestBid: nenv.Bid, t: float = 0.):
        dissues = self.preference.issues

        newBid = sugestBid.copy()
        index = self.chooseWorstIssue()

        values = self.preference.issues[index].values.copy()

        random.shuffle(values)

        my_utility = self.getMyUtility(t)

        for value in values:
            newBid[dissues[index]] = value

            if self.preference.get_utility(newBid) > my_utility:
                return newBid

        return newBid

        '''
        Old code takes long time
        
        dissues = self.preference.issues

        newBid = sugestBid.copy()
        index = self.chooseWorstIssue()
        loop = True
        bidTime = time.time()
        
        while loop:
            if time.time() - bidTime > 3:
                break

            newBid = sugestBid.copy()

            map = newBid.content
            map[self.preference.issues[index]] = self.getRandomValue(dissues[index])

            newBid = nenv.Bid(map)

            if self.preference.get_utility(newBid) > self.getMyUtility(t):
                return newBid

        return newBid
        '''

    def addBidToList(self, myBids: list, newBid: BidUtility):
        index = len(myBids)

        for i in range(len(myBids)):
            if myBids[i].utility <= newBid.utility:
                if myBids[i] != newBid.bid:
                    index = i
                else:
                    return

        myBids.insert(index, newBid)

    def calculateParamForOpponent(self, op: OpponentPreferences, bid: nenv.Bid):
        dissues = self.preference.issues
        bidVal = bid.content
        keys = list(bidVal.keys())

        for i in range(len(dissues)):
            if dissues[i] in op.repeatedIssue.keys():
                vals = op.repeatedIssue[dissues[i]]

                if bidVal[keys[i]] in vals.keys():
                    repet = vals[bidVal[keys[i]]]
                    repet += 1
                    vals[bidVal[keys[i]]] = repet
                else:
                    vals[bidVal[keys[i]]] = 1
            else:
                h = {}

                h[bidVal[keys[i]]] = 1

                op.repeatedIssue[dissues[i]] = h

    def setMyUtility(self, myUtility):
        self.myutility = myUtility

    def getMyUtility(self, t: float):
        myutility = self.getTargetUtility(t)

        if myutility < 0.7:
            return 0.7

        return myutility

    def getE(self):
        if self.withDiscount:
            return 0.2

        return 0.15

    def getRandomValue(self, issue):
        return random.choice(issue.values)

    def getTargetUtility(self, t: float):
        return 1 - math.pow(t, 1 / self.getE())
