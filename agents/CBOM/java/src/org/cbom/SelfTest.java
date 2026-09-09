package org.cbom;

import java.util.*;

/** Dependency-free native regressions; run with java -jar build/cbom.jar self-test. */
final class SelfTest {
    private SelfTest() {}
    private static void check(boolean condition, String message) { if (!condition) throw new IllegalStateException("Self-test failed: " + message); }
    static void run() {
        Preference profile = Preference.fromMap(Json.parse("{\"issueWeights\":{\"x\":1},\"issues\":{\"x\":{\"a\":1,\"b\":0.8,\"c\":0.5,\"d\":0}}}"));
        CBOMAgent agent = new CBOMAgent(profile, Json.map("mode", "exact"));
        agent.receive(Map.of("x", "b"), 0);
        check(agent.act(0).kind().equals("offer"), "counteroffer");
        check(agent.act(.8).kind().equals("offer"), "old offer cannot be accepted");
        agent.receive(Map.of("x", "b"), .9);
        check(agent.act(.9).kind().equals("accept"), "new received offer can be accepted");
        try { agent.act(1); throw new IllegalStateException("terminal action accepted"); }
        catch (IllegalStateException expected) { check(expected.getMessage().contains("already ended"), "terminal guard"); }
        Preference boundary = Preference.fromMap(Json.parse("{\"reservationValue\":0.8,\"issueWeights\":{\"x\":1},\"issues\":{\"x\":{\"best\":0.9,\"near\":0.7999999999995,\"feasible\":0.85,\"bad\":0}}}"));
        CBOMAgent edge = new CBOMAgent(boundary, Json.map("mode", "exact", "epsilon", 0));
        edge.act(0); edge.receive(Map.of("x", "bad"), .8);
        check(edge.act(.8).bid().get("x").equals("feasible"), "strict reservation boundary");
        ConflictBasedOpponentModel model = new ConflictBasedOpponentModel(profile, 2);
        model.update(Map.of("x", "a")); model.update(Map.of("x", "b")); model.update(Map.of("x", "c")); model.update(Map.of("x", "a"));
        check(model.observations() == 4 && model.comparisons() == 5, "history cap and persistent comparisons");
        Map<String, Object> before = model.state();
        try { model.update(Map.of("x", "missing")); throw new IllegalStateException("invalid bid accepted"); }
        catch (IllegalArgumentException expected) { check(before.equals(model.state()), "invalid update atomicity"); }
        check(Json.parse(Json.stringify(profile.toMap())).equals(Json.parse(Json.stringify(profile.toMap()))), "JSON roundtrip");
        System.out.println("Native Java regression checks passed");
    }
}
