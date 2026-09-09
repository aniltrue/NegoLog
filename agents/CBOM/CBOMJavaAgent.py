"""Run the actual Java CBOM implementation as a NegoLog tournament agent."""

from pathlib import Path

from .common import CBOMAdapter
from .java_bridge import JavaBridge


class CBOMJavaAgent(CBOMAdapter):
    """A persistent JVM per session; build the supplied JAR before negotiation."""

    java_executable = "java"
    java_jar = None
    request_timeout = 10.0

    @property
    def name(self):
        return "CBOMJava"

    def initiate(self, opponent_name):
        self.terminate(False, opponent_name, 0.)
        self._initialize_profile()
        jar = Path(self.java_jar) if self.java_jar else Path(__file__).parent / "java/build/cbom.jar"
        if not jar.is_file():
            raise FileNotFoundError(
                "CBOM Java has not been built. Run: python agents/CBOM/java/build.py"
            )
        self._bridge = JavaBridge([str(self.java_executable), "-jar", str(jar.resolve()), "serve"],
                                  self.request_timeout)
        try:
            self._bridge.request({"op": "init", "profile": self.cbom_preference.to_dict(),
                                  "options": dict(self.cbom_options)})
        except BaseException:
            self.terminate(False, opponent_name, 0.)
            raise

    def receive_offer(self, bid, t):
        content = self._bid_content(bid)
        self.cbom_preference.validate_bid(content)
        self._bridge.request({"op": "receive", "bid": content, "t": t})
        self._received(bid)

    def act(self, t):
        reply = self._bridge.request({"op": "act", "t": t})
        try:
            return self._action(reply.get("action", reply.get("result")))
        except BaseException:
            self._bridge.close()
            raise

    def terminate(self, is_accept, opponent_name, t):
        bridge = getattr(self, "_bridge", None)
        if bridge is not None:
            bridge.close()
