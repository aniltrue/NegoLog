"""Run the maintained CBOM model and paper strategy natively inside NegoLog."""

from ._vendor.cbom.strategy import CBOMAgent as CoreAgent
from ._vendor.cbom.model import ConflictBasedOpponentModel
from .common import CBOMAdapter


class CBOMAgent(CBOMAdapter):
    """Native Python CBOM; customize constructor settings using cbom_options."""

    @property
    def name(self):
        return "CBOM"

    def initiate(self, opponent_name):
        self._initialize_profile()
        options = dict(self.cbom_options)
        if "history_size" in options:
            if "model" in options:
                raise ValueError("Choose either history_size or a supplied model")
            options["model"] = ConflictBasedOpponentModel(
                self.cbom_preference, history_size=options.pop("history_size"))
        self.core = CoreAgent(self.cbom_preference, **options)

    def receive_offer(self, bid, t):
        content = self._bid_content(bid)
        self.core.receive(content, t)
        self._received(bid)

    def act(self, t):
        action = self.core.act(t)
        return self._action({"kind": action.kind, "bid": action.bid, "reason": action.reason})
