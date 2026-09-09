package org.cbom;

import java.math.BigInteger;
import java.util.*;

/** Immutable additive utility profile; construction never enumerates outcomes. */
public final class Preference {
    public final Map<String, Double> issueWeights;
    public final Map<String, Map<String, Double>> valueWeights;
    public final List<String> issues;
    public final Map<String, List<String>> domain;
    public final double reservation;
    public final BigInteger size;

    public Preference(Map<String, ?> weights, Map<String, ?> values, double reservation) {
        if (weights.isEmpty() || !weights.keySet().equals(values.keySet()))
            throw new IllegalArgumentException("Provide the same nonempty issues in both weight mappings");
        Map<String, Double> iw = new LinkedHashMap<>();
        Map<String, Map<String, Double>> vw = new LinkedHashMap<>();
        Map<String, List<String>> dom = new LinkedHashMap<>();
        BigInteger outcomes = BigInteger.ONE;
        double total = 0;
        for (var entry : weights.entrySet()) {
            String issue = entry.getKey();
            if (issue == null || issue.isEmpty()) throw new IllegalArgumentException("Issue names must be nonempty strings");
            double weight = unit(entry.getValue(), "Issue weight");
            iw.put(issue, weight); total += weight;
            Map<String, Object> items = Json.object(values.get(issue));
            if (items.isEmpty()) throw new IllegalArgumentException("Issue must contain values");
            Map<String, Double> evaluated = new LinkedHashMap<>();
            for (var item : items.entrySet()) {
                if (item.getKey().isEmpty()) throw new IllegalArgumentException("Value names must be nonempty strings");
                evaluated.put(item.getKey(), unit(item.getValue(), "Value utility"));
            }
            vw.put(issue, Collections.unmodifiableMap(evaluated));
            dom.put(issue, List.copyOf(evaluated.keySet()));
            outcomes = outcomes.multiply(BigInteger.valueOf(evaluated.size()));
        }
        if (Math.abs(total - 1) > 1e-9) throw new IllegalArgumentException("Issue weights must sum to one");
        this.issueWeights = Collections.unmodifiableMap(iw);
        this.valueWeights = Collections.unmodifiableMap(vw);
        this.domain = Collections.unmodifiableMap(dom);
        this.issues = List.copyOf(iw.keySet());
        this.reservation = unit(reservation, "Reservation utility");
        this.size = outcomes;
    }

    public static double unit(Object value, String name) {
        if (!(value instanceof Number n) || !Double.isFinite(n.doubleValue()) || n.doubleValue() < 0 || n.doubleValue() > 1)
            throw new IllegalArgumentException(name + " must be a finite number in [0, 1]");
        return n.doubleValue();
    }
    public static int positiveInt(Object value, String name) {
        if (!(value instanceof Number n) || value instanceof Double || value instanceof Float
                || !Double.isFinite(n.doubleValue()) || n.doubleValue() < 1
                || n.doubleValue() > Integer.MAX_VALUE || n.doubleValue() != n.intValue())
            throw new IllegalArgumentException(name + " must be a positive 32-bit integer");
        return n.intValue();
    }
    public static Preference fromMap(Object value) {
        var map = Json.object(value);
        return new Preference(Json.object(map.get("issueWeights")), Json.object(map.get("issues")),
                unit(map.getOrDefault("reservationValue", 0), "Reservation utility"));
    }
    public Map<String, Object> toMap() {
        return Json.map("reservationValue", reservation, "issueWeights", issueWeights, "issues", valueWeights);
    }
    public List<String> validateBid(Map<String, ?> bid) {
        if (bid == null || !bid.keySet().equals(issueWeights.keySet()))
            throw new IllegalArgumentException("A bid must contain exactly one value for every issue");
        List<String> encoded = new ArrayList<>();
        for (String issue : issues) {
            Object value = bid.get(issue);
            if (!(value instanceof String s) || !valueWeights.get(issue).containsKey(s))
                throw new IllegalArgumentException("Unknown value for issue " + issue + ": " + value);
            encoded.add((String)value);
        }
        return List.copyOf(encoded);
    }
    public Map<String, String> decode(List<String> encoded) {
        Map<String, String> result = new LinkedHashMap<>();
        for (int i = 0; i < issues.size(); i++) result.put(issues.get(i), encoded.get(i));
        return result;
    }
    public double utility(Map<String, ?> bid) {
        validateBid(bid);
        double[] terms = new double[issues.size()];
        for (int i = 0; i < issues.size(); i++) {
            String issue = issues.get(i);
            terms[i] = issueWeights.get(issue) * valueWeights.get(issue).get(bid.get(issue));
        }
        return Math.min(1.0, AccurateSum.sum(terms));
    }
    public Map<String, String> bestBid() {
        Map<String, String> result = new LinkedHashMap<>();
        for (String issue : issues) {
            String best = domain.get(issue).get(0);
            for (String value : domain.get(issue)) if (valueWeights.get(issue).get(value) > valueWeights.get(issue).get(best)) best = value;
            result.put(issue, best);
        }
        return result;
    }
}
