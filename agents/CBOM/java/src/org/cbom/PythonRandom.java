package org.cbom;

import java.math.BigInteger;

/** MT19937 integer seeding and randbelow follow Python random.Random. */
final class PythonRandom {
    private final int[] mt = new int[624];
    private int index = 624;
    PythonRandom(BigInteger seed) {
        seed = seed.abs();
        int[] key = new int[Math.max(1, (seed.bitLength() + 31) / 32)];
        for (int i = 0; i < key.length; i++) key[i] = seed.shiftRight(32 * i).intValue();
        mt[0] = 19650218;
        for (int i = 1; i < 624; i++) mt[i] = 1812433253 * (mt[i - 1] ^ (mt[i - 1] >>> 30)) + i;
        int i = 1, j = 0;
        for (int k = Math.max(624, key.length); k > 0; k--) {
            mt[i] = (mt[i] ^ (mt[i - 1] ^ (mt[i - 1] >>> 30)) * 1664525) + key[j] + j;
            i++; j++;
            if (i >= 624) { mt[0] = mt[623]; i = 1; }
            if (j >= key.length) j = 0;
        }
        for (int k = 623; k > 0; k--) {
            mt[i] = (mt[i] ^ (mt[i - 1] ^ (mt[i - 1] >>> 30)) * 1566083941) - i;
            i++;
            if (i >= 624) { mt[0] = mt[623]; i = 1; }
        }
        mt[0] = 0x80000000;
    }
    private int next() {
        if (index >= 624) {
            for (int i = 0; i < 624; i++) {
                int y = (mt[i] & 0x80000000) | (mt[(i + 1) % 624] & 0x7fffffff);
                mt[i] = mt[(i + 397) % 624] ^ (y >>> 1) ^ ((y & 1) == 0 ? 0 : 0x9908b0df);
            }
            index = 0;
        }
        int y = mt[index++];
        y ^= y >>> 11; y ^= (y << 7) & 0x9d2c5680; y ^= (y << 15) & 0xefc60000; y ^= y >>> 18;
        return y;
    }
    int below(int bound) {
        int bits = 32 - Integer.numberOfLeadingZeros(bound);
        int value;
        do { value = next() >>> (32 - bits); } while (value >= bound);
        return value;
    }
}
