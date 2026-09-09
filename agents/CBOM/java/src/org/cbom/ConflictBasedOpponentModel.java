package org.cbom;

import java.util.*;

/** Exact aggregated CBOM comparison evidence; no Python process is used. */
public final class ConflictBasedOpponentModel {
    private record Transition(String issue, String before, String after) {}
    private record Joint(Transition first, Transition second) {}
    private record IssuePair(String first, String second) {}
    public final Preference reference;
    public final int historySize;
    private final Deque<List<String>> history = new ArrayDeque<>();
    private final Map<List<String>, Long> offers = new LinkedHashMap<>();
    private final Map<Transition, Long> valueCounts = new HashMap<>();
    private final Map<Joint, Long> jointCounts = new HashMap<>();
    private final Map<String, List<String>> valueOrdering = new LinkedHashMap<>();
    private List<String> issueOrdering;
    private Preference preference;
    private long observations, comparisons;

    public ConflictBasedOpponentModel(Preference reference) { this(reference, 1000); }
    public ConflictBasedOpponentModel(Preference reference, int historySize) {
        if (historySize < 1) throw new IllegalArgumentException("history_size must be a positive integer");
        this.reference = reference; this.historySize = historySize;
        for (String issue : reference.issues) {
            List<String> reversed = new ArrayList<>(reference.domain.get(issue));
            Collections.reverse(reversed);
            Map<String, Double> inverse = new HashMap<>();
            double maximum = 0;
            for (String v : reversed) maximum = Math.max(maximum, 1 - reference.valueWeights.get(issue).get(v));
            for (String v : reversed) inverse.put(v, maximum == 0 ? 1 : (1 - reference.valueWeights.get(issue).get(v)) / maximum);
            valueOrdering.put(issue, StableOrder.sorted(reversed, Comparator.comparingDouble(inverse::get)));
        }
        List<String> reversed = new ArrayList<>(reference.issues);
        Collections.reverse(reversed);
        double total = 0;
        for (String issue : reference.issues) total += 1 - reference.issueWeights.get(issue);
        Map<String, Double> inverse = new HashMap<>();
        for (String issue : reversed) inverse.put(issue, total == 0 ? 1.0 / reversed.size() : (1 - reference.issueWeights.get(issue)) / total);
        issueOrdering = StableOrder.sorted(reversed, Comparator.comparingDouble(inverse::get));
        estimate();
    }
    public Preference preference() { return preference; }
    public long observations() { return observations; }
    public long comparisons() { return comparisons; }
    public int evidenceCells() { return valueCounts.size() + jointCounts.size(); }
    public Map<String, Object> state() {
        Map<String, Object> values = new LinkedHashMap<>();
        for (var e : valueOrdering.entrySet()) values.put(e.getKey(), List.copyOf(e.getValue()));
        return Json.map("preference", preference.toMap(), "value_ordering", values,
                "issue_ordering", List.copyOf(issueOrdering), "observations", observations,
                "comparisons", comparisons, "evidence_cells", evidenceCells());
    }
    public void update(Map<String, ?> bid) {
        List<String> current = reference.validateBid(bid);
        for (var entry : offers.entrySet()) {
            List<Transition> changes = new ArrayList<>();
            for (int i = 0; i < current.size(); i++) if (!entry.getKey().get(i).equals(current.get(i)))
                changes.add(new Transition(reference.issues.get(i), entry.getKey().get(i), current.get(i)));
            long count = entry.getValue();
            if (!changes.isEmpty()) comparisons = Math.addExact(comparisons, count);
            if (changes.size() == 1) valueCounts.merge(changes.get(0), count, Math::addExact);
            else for (int i = 0; i < changes.size(); i++) for (int j = i + 1; j < changes.size(); j++)
                jointCounts.merge(new Joint(changes.get(i), changes.get(j)), count, Math::addExact);
        }
        if (history.size() == historySize) {
            List<String> expired = history.removeFirst();
            long count = offers.get(expired) - 1;
            if (count == 0) offers.remove(expired); else offers.put(expired, count);
        }
        history.addLast(current); offers.merge(current, 1L, Math::addExact); observations++;
        Map<String, Map<String, Integer>> ranks = new HashMap<>();
        for (var entry : valueOrdering.entrySet()) {
            Map<String, Integer> order = new HashMap<>();
            for (int i = 0; i < entry.getValue().size(); i++) order.put(entry.getValue().get(i), i);
            ranks.put(entry.getKey(), order);
        }
        Map<IssuePair, Long> issueCounts = new HashMap<>();
        for (var entry : jointCounts.entrySet()) {
            Transition a = entry.getKey().first, b = entry.getKey().second;
            boolean lossA = ranks.get(a.issue).get(a.before) > ranks.get(a.issue).get(a.after);
            boolean lossB = ranks.get(b.issue).get(b.before) > ranks.get(b.issue).get(b.after);
            if (lossA != lossB) issueCounts.merge(lossA ? new IssuePair(a.issue, b.issue) : new IssuePair(b.issue, a.issue), entry.getValue(), Math::addExact);
        }
        for (String issue : reference.issues) valueOrdering.put(issue, StableOrder.sorted(reference.domain.get(issue), (a, b) -> {
            long difference = valueCounts.getOrDefault(new Transition(issue, a, b), 0L) - valueCounts.getOrDefault(new Transition(issue, b, a), 0L);
            if (difference == 0) difference = ranks.get(issue).get(a) - ranks.get(issue).get(b);
            return Long.compare(difference, 0);
        }));
        Map<String, Integer> previous = new HashMap<>();
        for (int i = 0; i < issueOrdering.size(); i++) previous.put(issueOrdering.get(i), i);
        issueOrdering = StableOrder.sorted(reference.issues, (a, b) -> {
            long difference = issueCounts.getOrDefault(new IssuePair(a, b), 0L) - issueCounts.getOrDefault(new IssuePair(b, a), 0L);
            if (difference == 0) difference = previous.get(a) - previous.get(b);
            return Long.compare(difference, 0);
        });
        estimate();
    }
    private void estimate() {
        double total = (double)issueOrdering.size() * (issueOrdering.size() + 1.0) / 2.0;
        Map<String, Double> weights = new LinkedHashMap<>();
        Map<String, Object> values = new LinkedHashMap<>();
        Map<String, Integer> issueRanks = new HashMap<>();
        for (int i = 0; i < issueOrdering.size(); i++) issueRanks.put(issueOrdering.get(i), i);
        for (String issue : reference.issues) {
            weights.put(issue, (issueRanks.get(issue) + 1) / total);
            Map<String, Double> items = new LinkedHashMap<>();
            List<String> order = valueOrdering.get(issue);
            Map<String, Integer> valueRanks = new HashMap<>();
            for (int i = 0; i < order.size(); i++) valueRanks.put(order.get(i), i);
            for (String value : reference.domain.get(issue)) items.put(value, (valueRanks.get(value) + 1.0) / order.size());
            values.put(issue, items);
        }
        preference = new Preference(weights, values, 0);
    }
}
