package org.cbom;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Small strict JSON codec. Objects retain input order, which resolves CBOM ties. */
@SuppressWarnings({"PMD.NPathComplexity"})
public final class Json {
    private Json() {}

    public static Object parse(String text) {
        Parser p = new Parser(text);
        Object result = p.value(0);
        p.space();
        if (p.at != text.length()) throw p.error("Trailing content");
        return result;
    }

    public static String stringify(Object value) {
        if (value == null) return "null";
        if (value instanceof String s) {
            StringBuilder b = new StringBuilder("\"");
            for (int i = 0; i < s.length(); i++) {
                char c = s.charAt(i);
                switch (c) {
                    case '"' -> b.append("\\\"");
                    case '\\' -> b.append("\\\\");
                    case '\b' -> b.append("\\b");
                    case '\f' -> b.append("\\f");
                    case '\n' -> b.append("\\n");
                    case '\r' -> b.append("\\r");
                    case '\t' -> b.append("\\t");
                    default -> { if (c < 32) b.append(String.format("\\u%04x", (int)c)); else b.append(c); }
                }
            }
            return b.append('"').toString();
        }
        if (value instanceof Number n) {
            if ((n instanceof Double || n instanceof Float) && !Double.isFinite(n.doubleValue()))
                throw new IllegalArgumentException("Non-finite JSON number");
            return n.toString();
        }
        if (value instanceof Boolean) return value.toString();
        if (value instanceof Map<?, ?> map) {
            List<String> parts = new ArrayList<>();
            for (var e : map.entrySet()) parts.add(stringify(e.getKey().toString()) + ":" + stringify(e.getValue()));
            return "{" + String.join(",", parts) + "}";
        }
        if (value instanceof Iterable<?> items) {
            List<String> parts = new ArrayList<>();
            for (Object item : items) parts.add(stringify(item));
            return "[" + String.join(",", parts) + "]";
        }
        throw new IllegalArgumentException("Unsupported JSON value: " + value.getClass());
    }

    @SuppressWarnings("unchecked")
    public static Map<String, Object> object(Object value) {
        if (!(value instanceof Map<?, ?> map)) throw new IllegalArgumentException("Expected a JSON object");
        for (Object key : map.keySet()) if (!(key instanceof String)) throw new IllegalArgumentException("Expected string keys");
        return (Map<String, Object>) map;
    }

    public static Map<String, Object> map(Object... pairs) {
        Map<String, Object> result = new LinkedHashMap<>();
        for (int i = 0; i < pairs.length; i += 2) result.put((String)pairs[i], pairs[i + 1]);
        return result;
    }

    private static final class Parser {
        final String text;
        int at;
        Parser(String text) { this.text = text; }
        IllegalArgumentException error(String message) { return new IllegalArgumentException(message + " at character " + at); }
        void space() { while (at < text.length() && " \r\n\t".indexOf(text.charAt(at)) >= 0) at++; }
        boolean take(char c) { if (at < text.length() && text.charAt(at) == c) { at++; return true; } return false; }
        Object value(int depth) {
            if (depth > 128) throw error("JSON nesting limit exceeded");
            space();
            if (at == text.length()) throw error("Missing value");
            char c = text.charAt(at);
            if (c == '"') return string();
            if (take('{')) {
                Map<String, Object> map = new LinkedHashMap<>();
                space();
                if (take('}')) return map;
                do {
                    space();
                    if (at == text.length() || text.charAt(at) != '"') throw error("Expected object key");
                    String key = string();
                    space();
                    if (!take(':')) throw error("Expected colon");
                    map.put(key, value(depth + 1));
                    space();
                    if (take('}')) return map;
                } while (take(','));
                throw error("Expected comma or closing brace");
            }
            if (take('[')) {
                List<Object> list = new ArrayList<>();
                space();
                if (take(']')) return list;
                do { list.add(value(depth + 1)); space(); if (take(']')) return list; } while (take(','));
                throw error("Expected comma or closing bracket");
            }
            for (String word : List.of("true", "false", "null")) {
                if (text.startsWith(word, at)) { at += word.length(); return word.equals("null") ? null : word.equals("true"); }
            }
            int start = at;
            take('-');
            if (!take('0')) {
                int digits = at;
                while (at < text.length() && text.charAt(at) >= '0' && text.charAt(at) <= '9') at++;
                if (at == digits) throw error("Expected number");
            }
            if (take('.')) digits();
            if (take('e') || take('E')) { if (!take('+')) take('-'); digits(); }
            try {
                String number = text.substring(start, at);
                if (number.indexOf('.') >= 0 || number.indexOf('e') >= 0 || number.indexOf('E') >= 0) return Double.valueOf(number);
                return new BigInteger(number);
            }
            catch (NumberFormatException e) { throw error("Invalid number"); }
        }
        void digits() {
            int start = at;
            while (at < text.length() && text.charAt(at) >= '0' && text.charAt(at) <= '9') at++;
            if (at == start) throw error("Missing number digits");
        }
        String string() {
            at++;
            StringBuilder b = new StringBuilder();
            while (at < text.length()) {
                char c = text.charAt(at++);
                if (c == '"') return b.toString();
                if (c < 32) throw error("Unescaped control character");
                if (c != '\\') { b.append(c); continue; }
                if (at == text.length()) throw error("Missing escape");
                switch (text.charAt(at++)) {
                    case '"' -> b.append('"'); case '\\' -> b.append('\\'); case '/' -> b.append('/');
                    case 'b' -> b.append('\b'); case 'f' -> b.append('\f'); case 'n' -> b.append('\n');
                    case 'r' -> b.append('\r'); case 't' -> b.append('\t');
                    case 'u' -> {
                        if (at + 4 > text.length()) throw error("Incomplete Unicode escape");
                        for (int i = at; i < at + 4; i++)
                            if ("0123456789abcdefABCDEF".indexOf(text.charAt(i)) < 0)
                                throw error("Invalid Unicode escape");
                        try { b.append((char)Integer.parseInt(text.substring(at, at + 4), 16)); }
                        catch (NumberFormatException e) { throw error("Invalid Unicode escape"); }
                        at += 4;
                    }
                    default -> throw error("Invalid escape");
                }
            }
            throw error("Unterminated string");
        }
    }
}
