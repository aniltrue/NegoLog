package org.cbom;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;

/**
 * CPython 3.10 TimSort, preserving the comparison and merge schedule for cycles.
 * Adapted from CPython v3.10.20 Objects/listobject.c: binarysort, count_run,
 * gallop_left/right, merge_lo/hi/at/collapse/force_collapse and minrun.
 * Copyright (c) 2001-2023 Python Software Foundation. All Rights Reserved.
 * Source: https://github.com/python/cpython/blob/v3.10.20/Objects/listobject.c
 * License: java/PSF-LICENSE. Changes: Java arrays, generics, exceptions, automatic
 * storage management; omitted Python object/key handling. No Python runtime used.
 */
final class StableOrder {
    private StableOrder() {}
    static <T> List<T> sorted(List<T> input, Comparator<T> compare) {
        return new Sorter<T>(input, compare).sort();
    }
    private record Run(int base, int length) {}
    @SuppressWarnings({"PMD.AvoidReassigningParameters", "PMD.NPathComplexity"})
    private static final class Sorter<T> {
        private static final int MIN_GALLOP = 7;
        private final Object[] values;
        private final Comparator<T> compare;
        private final List<Run> pending = new ArrayList<>();
        private int minGallop = MIN_GALLOP;
        Sorter(List<T> input, Comparator<T> compare) { values = input.toArray(); this.compare = compare; }
        @SuppressWarnings("unchecked")
        private boolean less(Object left, Object right) { return compare.compare((T)left, (T)right) < 0; }
        @SuppressWarnings("unchecked")
        List<T> sort() {
            if (values.length > 1) {
                int minimum = minrun(values.length);
                int base = 0;
                while (base < values.length) {
                    int length = countRun(base);
                    if (length < minimum) {
                        int force = Math.min(minimum, values.length - base);
                        binarySort(base, base + force, base + length);
                        length = force;
                    }
                    pending.add(new Run(base, length));
                    collapse();
                    base += length;
                }
                while (pending.size() > 1) {
                    int n = pending.size() - 2;
                    if (n > 0 && pending.get(n - 1).length < pending.get(n + 1).length) n--;
                    mergeAt(n);
                }
            }
            List<T> result = new ArrayList<>(values.length);
            for (Object value : values) result.add((T)value);
            return result;
        }
        private static int minrun(int size) {
            int remainder = 0;
            while (size >= 64) { remainder |= size & 1; size >>= 1; }
            return size + remainder;
        }
        private int countRun(int base) {
            if (base + 1 == values.length) return 1;
            int length = 2;
            boolean descending = less(values[base + 1], values[base]);
            while (base + length < values.length) {
                boolean smaller = less(values[base + length], values[base + length - 1]);
                if (descending != smaller) break;
                length++;
            }
            if (descending) {
                int left = base;
                int right = base + length - 1;
                for ( ; left < right; left++, right--) {
                    Object value = values[left];
                    values[left] = values[right];
                    values[right] = value;
                }
            }
            return length;
        }
        private void binarySort(int base, int end, int start) {
            if (start == base) start++;
            for (; start < end; start++) {
                Object pivot = values[start];
                int left = base;
                int right = start;
                do {
                    int middle = left + ((right - left) >>> 1);
                    if (less(pivot, values[middle])) right = middle; else left = middle + 1;
                } while (left < right);
                System.arraycopy(values, left, values, left + 1, start - left);
                values[left] = pivot;
            }
        }
        private void collapse() {
            while (pending.size() > 1) {
                int n = pending.size() - 2;
                if ((n > 0 && pending.get(n - 1).length <= pending.get(n).length + pending.get(n + 1).length)
                        || (n > 1 && pending.get(n - 2).length <= pending.get(n - 1).length + pending.get(n).length)) {
                    if (pending.get(n - 1).length < pending.get(n + 1).length) n--;
                    mergeAt(n);
                } else if (pending.get(n).length <= pending.get(n + 1).length) mergeAt(n);
                else break;
            }
        }
        private void mergeAt(int index) {
            Run left = pending.get(index);
            Run right = pending.remove(index + 1);
            pending.set(index, new Run(left.base, left.length + right.length));
            int baseA = left.base;
            int na = left.length;
            int baseB = right.base;
            int nb = right.length;
            int skipped = gallopRight(values[baseB], values, baseA, na, 0);
            baseA += skipped; na -= skipped;
            if (na == 0) return;
            nb = gallopLeft(values[baseA + na - 1], values, baseB, nb, nb - 1);
            if (nb == 0) return;
            if (na <= nb) mergeLo(baseA, na, baseB, nb); else mergeHi(baseA, na, baseB, nb);
        }
        private static int grow(int offset, int maximum) {
            return offset > (maximum - 1) / 2 ? maximum : 2 * offset + 1;
        }
        private int gallopLeft(Object key, Object[] array, int base, int length, int hint) {
            int last = 0;
            int offset = 1;
            if (less(array[base + hint], key)) {
                int maximum = length - hint;
                while (offset < maximum) {
                    if (!less(array[base + hint + offset], key)) break;
                    last = offset; offset = grow(offset, maximum);
                }
                offset = Math.min(offset, maximum); last += hint; offset += hint;
            } else {
                int maximum = hint + 1;
                while (offset < maximum) {
                    if (less(array[base + hint - offset], key)) break;
                    last = offset; offset = grow(offset, maximum);
                }
                offset = Math.min(offset, maximum);
                int oldLast = last; last = hint - offset; offset = hint - oldLast;
            }
            last++;
            while (last < offset) {
                int middle = last + ((offset - last) >>> 1);
                if (less(array[base + middle], key)) last = middle + 1; else offset = middle;
            }
            return offset;
        }
        private int gallopRight(Object key, Object[] array, int base, int length, int hint) {
            int last = 0;
            int offset = 1;
            if (less(key, array[base + hint])) {
                int maximum = hint + 1;
                while (offset < maximum) {
                    if (!less(key, array[base + hint - offset])) break;
                    last = offset; offset = grow(offset, maximum);
                }
                offset = Math.min(offset, maximum);
                int oldLast = last; last = hint - offset; offset = hint - oldLast;
            } else {
                int maximum = length - hint;
                while (offset < maximum) {
                    if (less(key, array[base + hint + offset])) break;
                    last = offset; offset = grow(offset, maximum);
                }
                offset = Math.min(offset, maximum); last += hint; offset += hint;
            }
            last++;
            while (last < offset) {
                int middle = last + ((offset - last) >>> 1);
                if (less(key, array[base + middle])) offset = middle; else last = middle + 1;
            }
            return offset;
        }
        private void copyB(Object[] temp, int a, int b, int nb, int destination) {
            System.arraycopy(values, b, values, destination, nb); values[destination + nb] = temp[a];
        }
        private void mergeLo(int baseA, int na, int baseB, int nb) {
            Object[] temp = Arrays.copyOfRange(values, baseA, baseA + na);
            int a = 0;
            int b = baseB;
            int destination = baseA;
            values[destination++] = values[b++];
            if (--nb == 0) { System.arraycopy(temp, a, values, destination, na); return; }
            if (na == 1) { copyB(temp, a, b, nb, destination); return; }
            int threshold = minGallop;
            for (;;) {
                int countA = 0;
                int countB = 0;
                for (;;) {
                    if (less(values[b], temp[a])) {
                        values[destination++] = values[b++]; countB++; countA = 0;
                        if (--nb == 0) { System.arraycopy(temp, a, values, destination, na); return; }
                        if (countB >= threshold) break;
                    } else {
                        values[destination++] = temp[a++]; countA++; countB = 0;
                        if (--na == 1) { copyB(temp, a, b, nb, destination); return; }
                        if (countA >= threshold) break;
                    }
                }
                threshold++;
                do {
                    if (threshold > 1) threshold--;
                    minGallop = threshold;
                    countA = gallopRight(values[b], temp, a, na, 0);
                    if (countA != 0) {
                        System.arraycopy(temp, a, values, destination, countA);
                        destination += countA; a += countA; na -= countA;
                        if (na == 1) { copyB(temp, a, b, nb, destination); return; }
                        if (na == 0) return; // Nontransitive comparator can exhaust A here.
                    }
                    values[destination++] = values[b++];
                    if (--nb == 0) { System.arraycopy(temp, a, values, destination, na); return; }
                    countB = gallopLeft(temp[a], values, b, nb, 0);
                    if (countB != 0) {
                        System.arraycopy(values, b, values, destination, countB);
                        destination += countB; b += countB; nb -= countB;
                        if (nb == 0) { System.arraycopy(temp, a, values, destination, na); return; }
                    }
                    values[destination++] = temp[a++];
                    if (--na == 1) { copyB(temp, a, b, nb, destination); return; }
                } while (countA >= MIN_GALLOP || countB >= MIN_GALLOP);
                minGallop = ++threshold;
            }
        }
        private void copyA(Object[] temp, int b, int a, int na, int destination) {
            System.arraycopy(values, a - na + 1, values, destination - na + 1, na);
            values[destination - na] = temp[b];
        }
        private void mergeHi(int baseA, int na, int baseB, int nb) {
            Object[] temp = Arrays.copyOfRange(values, baseB, baseB + nb);
            int a = baseA + na - 1;
            int b = nb - 1;
            int destination = baseB + nb - 1;
            values[destination--] = values[a--];
            if (--na == 0) { System.arraycopy(temp, 0, values, destination - nb + 1, nb); return; }
            if (nb == 1) { copyA(temp, b, a, na, destination); return; }
            int threshold = minGallop;
            for (;;) {
                int countA = 0;
                int countB = 0;
                for (;;) {
                    if (less(temp[b], values[a])) {
                        values[destination--] = values[a--]; countA++; countB = 0;
                        if (--na == 0) { System.arraycopy(temp, 0, values, destination - nb + 1, nb); return; }
                        if (countA >= threshold) break;
                    } else {
                        values[destination--] = temp[b--]; countB++; countA = 0;
                        if (--nb == 1) { copyA(temp, b, a, na, destination); return; }
                        if (countB >= threshold) break;
                    }
                }
                threshold++;
                do {
                    if (threshold > 1) threshold--;
                    minGallop = threshold;
                    countA = na - gallopRight(temp[b], values, baseA, na, na - 1);
                    if (countA != 0) {
                        System.arraycopy(values, a - countA + 1, values, destination - countA + 1, countA);
                        destination -= countA; a -= countA; na -= countA;
                        if (na == 0) { System.arraycopy(temp, 0, values, destination - nb + 1, nb); return; }
                    }
                    values[destination--] = temp[b--];
                    if (--nb == 1) { copyA(temp, b, a, na, destination); return; }
                    countB = nb - gallopLeft(values[a], temp, 0, nb, nb - 1);
                    if (countB != 0) {
                        System.arraycopy(temp, b - countB + 1, values, destination - countB + 1, countB);
                        destination -= countB; b -= countB; nb -= countB;
                        if (nb == 1) { copyA(temp, b, a, na, destination); return; }
                        if (nb == 0) return; // Nontransitive comparator can exhaust B here.
                    }
                    values[destination--] = values[a--];
                    if (--na == 0) { System.arraycopy(temp, 0, values, destination - nb + 1, nb); return; }
                } while (countA >= MIN_GALLOP || countB >= MIN_GALLOP);
                minGallop = ++threshold;
            }
        }
    }
}
