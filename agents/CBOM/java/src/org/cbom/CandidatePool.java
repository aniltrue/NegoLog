package org.cbom;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Finite exact or fixed-seed sampled candidate index. */
@SuppressWarnings({"PMD.AvoidReassigningParameters", "PMD.NPathComplexity"})
public final class CandidatePool {
    public final Preference preference;
    public final boolean exact;
    private final List<Entry> entries = new ArrayList<>();
    public CandidatePool(Preference preference, String mode, int maxExact, int sampleSize, BigInteger seed) {
        if (mode == null || !List.of("auto", "exact", "sampled").contains(mode)) throw new IllegalArgumentException("Search mode must be auto, exact or sampled");
        if (maxExact < 1 || sampleSize < 1) throw new IllegalArgumentException("Candidate limits must be positive integers");
        this.preference = preference;
        exact = mode.equals("exact") || (mode.equals("auto") && preference.size.compareTo(BigInteger.valueOf(maxExact)) <= 0);
        if (exact && preference.size.compareTo(BigInteger.valueOf(maxExact)) > 0)
            throw new IllegalArgumentException("Exact search exceeds max_exact_outcomes; raise the explicit limit or use sampled");
        if (exact) enumerate();
        else {
            PythonRandom rng = new PythonRandom(seed);
            Set<List<String>> candidates = new LinkedHashSet<>();
            candidates.add(preference.validateBid(preference.bestBid()));
            for (int k = 1; k < sampleSize; k++) {
                List<String> encoded = new ArrayList<>();
                for (String issue : preference.issues) {
                    List<String> values = preference.domain.get(issue);
                    encoded.add(values.get(rng.below(values.size())));
                }
                candidates.add(List.copyOf(encoded));
            }
            for (List<String> encoded : candidates) add(encoded);
        }
        entries.sort(Comparator.comparingDouble(Entry::utility));
    }
    private record Entry(double utility, List<String> encoded) {}
    public record Selection(Map<String, String> bid, double ownUtility, Double opponentUtility,
                           double epsilon, int candidateCount, boolean exact) {
        public Map<String, Object> toMap() { return Json.map("bid", bid, "own_utility", ownUtility,
                "opponent_utility", opponentUtility, "epsilon", epsilon, "candidate_count", candidateCount, "exact", exact); }
    }
    public static final class NoAvailableBid extends RuntimeException {
        public NoAvailableBid() { super("No unused bid at or above reservation remains in the candidate pool"); }
    }
    private void enumerate() {
        // Mixed-radix iteration matches itertools.product without consuming one
        // Java stack frame per issue (many singleton issues still mean one bid).
        List<List<String>> domains = new ArrayList<>(preference.domain.values());
        int[] indices = new int[domains.size()];
        while (true) {
            List<String> encoded = new ArrayList<>(indices.length);
            for (int i = 0; i < indices.length; i++) encoded.add(domains.get(i).get(indices[i]));
            add(List.copyOf(encoded));
            int carry = indices.length - 1;
            while (carry >= 0 && ++indices[carry] == domains.get(carry).size()) {
                indices[carry] = 0;
                carry--;
            }
            if (carry < 0) return;
        }
    }
    private void add(List<String> encoded) { entries.add(new Entry(preference.utility(preference.decode(encoded)), encoded)); }
    public int size() { return entries.size(); }
    public Selection select(double target, double epsilon, Set<List<String>> excluded, Preference opponent) {
        Preference.unit(target, "Target utility");
        Preference.unit(epsilon, "Initial epsilon");
        Set<List<String>> blocked = excluded == null ? Set.of() : excluded;
        if (opponent != null && !opponent.domain.equals(preference.domain))
            throw new IllegalArgumentException("Opponent profile must have the same ordered domain");
        double nearest = Double.POSITIVE_INFINITY;
        for (Entry e : entries) {
            if (!blocked.contains(e.encoded) && e.utility >= preference.reservation)
            nearest = Math.min(nearest, Math.abs(e.utility - target));
        }
        if (!Double.isFinite(nearest)) throw new NoAvailableBid();
        double steps = Math.max(0, Math.ceil((nearest - epsilon - 1e-12) / .01));
        double width = epsilon + steps * .01;
        double lower = target - width - 1e-12;
        double upper = target + width + 1e-12;
        Selection selected = null;
        double best = Double.NEGATIVE_INFINITY;
        int count = 0;
        for (Entry e : entries) {
            if (e.utility < lower || e.utility > upper || blocked.contains(e.encoded) || e.utility < preference.reservation)
                continue;
            count++;
            Map<String, String> bid = preference.decode(e.encoded);
            Double other = opponent == null ? null : opponent.utility(bid);
            double score = other == null ? e.utility : e.utility * other;
            if (score > best) { best = score; selected = new Selection(bid, e.utility, other, width, 0, exact); }
        }
        if (selected == null) throw new IllegalStateException("Candidate band did not contain its nearest eligible bid");
        return new Selection(selected.bid, selected.ownUtility, selected.opponentUtility, width, count, exact);
    }
}
