import random
from typing import List, Optional
import agents
from agents.Caduceus2015.UtilFunctions import *
import nenv


class Caduceus(nenv.AbstractAgent):
    """
        **Caduceus agent by Taha Güneş**:
            Inspired from the ideas such as *"algorithm portfolio"*, *"mixture of experts"*, and *"genetic algorithm"*,
            this agent presents two novel negotiation strategies, which combine multiple negotiation experts to decide
            what to bid and what to accept during the negotiation. In the first approach namely incremental portfolio,
            a bid is constructed by asking each negotiation agent’s opinion in the portfolio and picking one of the
            suggestions stochastically considering the expertise levels of the agents. In the second approach namely
            crossover strategy, each expert agent makes a bid suggestion and a majority voting is used on each issue
            value to decide the bid content. The proposed approaches have been evaluated empirically and our
            experimental results showed that the crossover strategy outperformed the top five finalists of the ANAC 2016
            Negotiation Competition in terms of the obtained average individual utility. [Gunes2017]_

        ANAC 2016 individual utility category winner.

        .. [Gunes2017] Güneş, T.D., Arditi, E., Aydoğan, R. (2017). Collective Voice of Experts in Multilateral Negotiation. In: An, B., Bazzan, A., Leite, J., Villata, S., van der Torre, L. (eds) PRIMA 2017: Principles and Practice of Multi-Agent Systems. PRIMA 2017. Lecture Notes in Computer Science(), vol 10621. Springer, Cham. <https://doi.org/10.1007/978-3-319-69131-2_27>
    """
    discountFactor: float
    selfReservationValue: float
    percentageOfOfferingBestBid: float
    random: random.Random
    agents: List[nenv.AbstractAgent]
    scores: List[float]

    def getScore(self, agentIndex: int):
        return self.scores[agentIndex]

    def initiate(self, opponent_name: Optional[str]):
        self.random = random.Random()
        self.discountFactor = 1.
        self.selfReservationValue = max(0.75, self.preference.reservation_value)
        self.scores = normalize([100, 10, 5, 3, 1])
        self.percentageOfOfferingBestBid = 0.83

        self.agents = [
            agents.ParsAgent(self.preference, self.session_time, []),
            agents.RandomDance(self.preference, self.session_time, []),
            agents.Kawaii(self.preference, self.session_time, []),
            agents.Atlas3Agent(self.preference, self.session_time, []),
            agents.Caduceus2015(self.preference, self.session_time, [])
        ]

        for agent in self.agents:
            agent.initiate(opponent_name)

    @property
    def name(self) -> str:
        return "Caduceus"

    def act(self, t: float) -> nenv.Action:
        if self.isBestOfferTime(t):
            return nenv.Offer(self.preference.bids[0])

        bidsFromAgents = []
        possibleActions = []

        for agent in self.agents:
            possibleActions.append(agent.act(t))

        scoreOfAccepts = 0
        scoreOfBids = 0

        agentsWithBids = []

        for i, action in enumerate(possibleActions):
            if isinstance(action, nenv.Accept):
                scoreOfAccepts += self.getScore(i)
            else:
                scoreOfBids += self.getScore(i)
                bidsFromAgents.append(action.bid)
                agentsWithBids.append(i)

        if self.can_accept() and scoreOfAccepts > scoreOfBids:
            return self.accept_action
        elif scoreOfBids > scoreOfAccepts:
            return nenv.Offer(self.getRandomizedAction(agentsWithBids, bidsFromAgents))

        return nenv.Offer(self.preference.bids[0])

    def getRandomizedAction(self, agentsWithBids: list, bidsFromAgents: list):
        possibilities = [self.getScore(agentWithBid) for agentWithBid in agentsWithBids]

        possibilities = normalize(possibilities)

        randomPick = self.random.random()

        acc = 0.
        for i, possibility in enumerate(possibilities):
            acc += possibility

            if randomPick < acc:
                return bidsFromAgents[i]

        return bidsFromAgents[-1]

    def receive_offer(self, bid: nenv.Bid, t: float):
        for agent in self.agents:
            agent.receive_bid(bid, t)

    def isBestOfferTime(self, t: float):
        return t < self.percentageOfOfferingBestBid
