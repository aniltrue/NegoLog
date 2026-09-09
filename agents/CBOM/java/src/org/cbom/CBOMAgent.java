package org.cbom;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Native Java CBOM bidding and acceptance strategy (paper Algorithm 2). */
@SuppressWarnings({"PMD.AvoidReassigningParameters", "PMD.NPathComplexity"})
public final class CBOMAgent {
    private static final double[][] BEHAVIOR_WEIGHTS = {
        {}, {1}, {.25, .75}, {.11, .22, .66}, {.05, .15, .3, .5}
    };

    public final Preference preference;
    public final ConflictBasedOpponentModel model;
    public final CandidatePool pool;
    private final double p0;
    private final double p1;
    private final double p2;
    private final double p3;
    private final double epsilon;
    private final int modelThreshold;
    private final List<Map<String, String>> ownHistory = new ArrayList<>();
    private final List<Map<String, String>> opponentHistory = new ArrayList<>();
    private final List<Double> ownUtilities = new ArrayList<>();
    private final List<Double> opponentUtilities = new ArrayList<>();
    private final Set<List<String>> offered = new HashSet<>();
    private boolean terminal;
    private boolean pendingOffer;
    private double lastTime;

    public record Action(String kind, Map<String, String> bid, Double ownUtility, double target,
                         CandidatePool.Selection selection, String reason) {
        public Map<String, Object> toMap() {
            return Json.map("kind", kind, "bid", bid,
                    "own_utility", ownUtility, "target", target, "selection",
                    selection == null ? null : selection.toMap(), "reason", reason);
        }
    }

    public CBOMAgent(Preference preference) { this(preference, Map.of()); }
    public CBOMAgent(Preference preference, Map<String, Object> options) {
        Set<String> names = Set.of("p0", "p1", "p2", "p3", "epsilon", "model_threshold", "history_size", "mode", "max_exact_outcomes", "sample_size", "seed");
        for (String key : options.keySet()) if (!names.contains(key)) throw new IllegalArgumentException("Unknown agent option: " + key);
        this.preference = preference;
        p0 = unitOption(options, "p0", .9); p1 = unitOption(options, "p1", .7);
        p2 = unitOption(options, "p2", .4); p3 = unitOption(options, "p3", .5);
        epsilon = unitOption(options, "epsilon", .02);
        modelThreshold = intOption(options, "model_threshold", 3);
        Object mode = options.getOrDefault("mode", "auto");
        if (!(mode instanceof String)) throw new IllegalArgumentException("Search mode must be auto, exact or sampled");
        model = new ConflictBasedOpponentModel(preference, intOption(options, "history_size", 1000));
        pool = new CandidatePool(preference, (String)mode, intOption(options, "max_exact_outcomes", 50000),
                intOption(options, "sample_size", 4096), integerSeed(options.getOrDefault("seed", 0)));
    }
    private static double unitOption(Map<String, Object> options, String key, double fallback) {
        return Preference.unit(options.getOrDefault(key, fallback), key);
    }
    private static int intOption(Map<String, Object> options, String key, int fallback) {
        return Preference.positiveInt(options.getOrDefault(key, fallback), key);
    }
    static BigInteger integerSeed(Object value) {
        if (!(value instanceof Number number)) throw new IllegalArgumentException("Java seed must be an integer");
        try { return new BigDecimal(number.toString()).toBigIntegerExact(); }
        catch (ArithmeticException | NumberFormatException e) { throw new IllegalArgumentException("Java seed must be an integer"); }
    }
    public List<Map<String, String>> ownHistory() { return snapshots(ownHistory); }
    public List<Map<String, String>> opponentHistory() { return snapshots(opponentHistory); }
    private static List<Map<String, String>> snapshots(List<Map<String, String>> history) {
        List<Map<String, String>> copied = new ArrayList<>();
        for (Map<String, String> bid : history) copied.add(new LinkedHashMap<>(bid));
        return copied;
    }
    private double eventTime(double t) {
        if (terminal) throw new IllegalStateException("The negotiation has already ended");
        Preference.unit(t, "Normalized time");
        if (t < lastTime) throw new IllegalArgumentException("Negotiation time must be nondecreasing");
        return t;
    }
    public void receive(Map<String, ?> bid, double t) {
        t = eventTime(t);
        double utility = preference.utility(bid);
        Map<String, String> snapshot = preference.decode(preference.validateBid(bid));
        model.update(snapshot);
        opponentHistory.add(snapshot); opponentUtilities.add(utility); lastTime = t; pendingOffer = true;
    }
    public double timeBased(double t) {
        Preference.unit(t, "Normalized time");
        return (1 - t) * (1 - t) * p0 + 2 * (1 - t) * t * p1 + t * t * p2;
    }
    public double targetUtility(double t) {
        Preference.unit(t, "Normalized time");
        double target = timeBased(t);
        if (!ownUtilities.isEmpty() && opponentUtilities.size() >= 2) {
            int start = Math.max(0, opponentUtilities.size() - 5);
            int length = opponentUtilities.size() - start - 1;
            double delta = 0;
            for (int i = 0; i < length; i++) delta += (opponentUtilities.get(start + i + 1) - opponentUtilities.get(start + i)) * BEHAVIOR_WEIGHTS[length][i];
            double behavior = ownUtilities.get(ownUtilities.size() - 1) - (p3 + p3 * t) * delta;
            target = (1 - t * t) * behavior + t * t * target;
        }
        double maximum = preference.utility(preference.bestBid());
        return Math.max(preference.reservation, Math.min(maximum, target));
    }
    private boolean canAccept(Double candidate) {
        if (!pendingOffer || (candidate == null && ownUtilities.isEmpty())) return false;
        double floor = candidate == null ? Double.POSITIVE_INFINITY : candidate;
        for (double utility : ownUtilities) floor = Math.min(floor, utility);
        floor = Math.max(preference.reservation, floor);
        return opponentUtilities.get(opponentUtilities.size() - 1) >= floor;
    }
    private Action accept(double target, CandidatePool.Selection selection) {
        terminal = true;
        return new Action("accept", new LinkedHashMap<>(opponentHistory.get(opponentHistory.size() - 1)),
                opponentUtilities.get(opponentUtilities.size() - 1), target, selection,
                "received offer meets the historical acceptance floor");
    }
    private Action end(double target, String reason) { terminal = true; return new Action("end", null, null, target, null, reason); }
    public Action act(double t) {
        t = eventTime(t);
        double target = targetUtility(t);
        double maximum = preference.utility(preference.bestBid());
        lastTime = t;
        if (maximum < preference.reservation) return end(target, "no outcome meets reservation utility");
        boolean opening = ownHistory.isEmpty();
        Preference estimated = !opening && opponentHistory.size() >= modelThreshold ? model.preference() : null;
        CandidatePool.Selection selection;
        try { selection = pool.select(opening ? maximum : target, opening ? 0 : epsilon, offered, estimated); }
        catch (CandidatePool.NoAvailableBid e) {
            if (canAccept(null)) return accept(target, null);
            return end(target, "candidate pool exhausted");
        }
        if (canAccept(selection.ownUtility())) return accept(target, selection);
        if (t == 1) return end(target, "deadline reached");
        if (selection.ownUtility() < preference.reservation) return end(target, "candidate does not meet reservation utility");
        Map<String, String> bid = new LinkedHashMap<>(selection.bid());
        ownHistory.add(bid); ownUtilities.add(selection.ownUtility()); offered.add(preference.validateBid(bid));
        pendingOffer = false;
        return new Action("offer", new LinkedHashMap<>(bid), selection.ownUtility(), target, selection,
                opening ? "own-utility opening" : "hybrid candidate selection");
    }
}
