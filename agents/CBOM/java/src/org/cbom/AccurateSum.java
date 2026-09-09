package org.cbom;

/** Error-free partial summation, including the final half-even correction. */
@SuppressWarnings("PMD.NPathComplexity")
final class AccurateSum {
    private AccurateSum() {}
    static double sum(double[] values) {
        double[] partials = new double[values.length];
        int n = 0;
        for (double x : values) {
            int i = 0;
            for (int j = 0; j < n; j++) {
                double y = partials[j];
                if (Math.abs(x) < Math.abs(y)) {
                    double temp = x;
                    x = y;
                    y = temp;
                }
                double hi = x + y;
                double lo = y - (hi - x);
                if (lo != 0) partials[i++] = lo;
                x = hi;
            }
            n = i;
            if (x != 0) partials[n++] = x;
        }
        double hi = 0;
        double lo = 0;
        if (n > 0) {
            hi = partials[--n];
            while (n > 0) {
                double x = hi;
                double y = partials[--n];
                hi = x + y;
                lo = y - (hi - x);
                if (lo != 0) break;
            }
            if (n > 0 && ((lo < 0 && partials[n - 1] < 0) || (lo > 0 && partials[n - 1] > 0))) {
                double y = lo * 2;
                double x = hi + y;
                if (y == x - hi) hi = x;
            }
        }
        return hi;
    }
}
