package org.cbom;

import java.io.*;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** Standalone CLI and persistent JSON-lines bridge for embedding in frameworks. */
public final class Main {
    public static final String VERSION = "1.1.0";
    private Main() {}
    public static void main(String[] args) {
        try {
            if (args.length == 0 || args[0].equals("--help")) { usage(); return; }
            switch (args[0]) {
                case "--version" -> System.out.println("CBOM Java " + VERSION);
                case "serve" -> serve();
                case "demo" -> demo(options(args));
                case "learn" -> learn(options(args));
                case "self-test" -> SelfTest.run();
                default -> throw new IllegalArgumentException("Unknown command: " + args[0]);
            }
        } catch (IOException | IllegalArgumentException | IllegalStateException error) {
            System.err.println("CBOM error: " + error.getMessage());
            System.exit(2);
        }
    }
    private static void usage() {
        System.out.println("CBOM Java " + VERSION + " (JDK 17+, no runtime dependencies)\n"
                + "  demo [--profile-a FILE --profile-b FILE] [--rounds 30] [--seed 0]\n"
                + "       [--search-mode auto|exact|sampled] [--sample-size 4096] [--output FILE]\n"
                + "  learn --profile FILE --offers JSONL [--history-size 1000] [--output FILE]\n"
                + "  serve        persistent JSON-lines agent protocol\n  self-test    native regression checks\n  --version");
    }
    private static Map<String, String> options(String[] args) {
        Map<String, String> result = new LinkedHashMap<>();
        for (int i = 1; i < args.length; i += 2) {
            if (!args[i].startsWith("--") || i + 1 == args.length) throw new IllegalArgumentException("Expected --option value");
            result.put(args[i].substring(2), args[i + 1]);
        }
        return result;
    }
    private static void checkOptions(Map<String, String> options, Set<String> names) {
        for (String option : options.keySet()) if (!names.contains(option)) throw new IllegalArgumentException("Unknown option: --" + option);
    }
    private static Preference readProfile(String path) throws IOException {
        if (path == null) throw new IllegalArgumentException("Missing required --profile");
        return Preference.fromMap(Json.parse(Files.readString(Path.of(path), StandardCharsets.UTF_8)));
    }
    public static Preference exampleProfile(String side) throws IOException {
        try (InputStream data = Main.class.getResourceAsStream("/data/profile_" + side + ".json")) {
            if (data == null) throw new IOException("Missing packaged example profile");
            return Preference.fromMap(Json.parse(new String(data.readAllBytes(), StandardCharsets.UTF_8)));
        }
    }
    private static void write(String path, Object value) throws IOException {
        Path output = Path.of(path);
        if (output.toAbsolutePath().getParent() != null) Files.createDirectories(output.toAbsolutePath().getParent());
        Files.writeString(output, Json.stringify(value) + "\n", StandardCharsets.UTF_8);
    }
    private static void demo(Map<String, String> opts) throws IOException {
        checkOptions(opts, Set.of("profile-a", "profile-b", "rounds", "seed", "search-mode", "sample-size", "output"));
        if (opts.containsKey("profile-a") != opts.containsKey("profile-b")) throw new IllegalArgumentException("Provide both --profile-a and --profile-b, or neither");
        Preference a = opts.containsKey("profile-a") ? readProfile(opts.get("profile-a")) : exampleProfile("a");
        Preference b = opts.containsKey("profile-b") ? readProfile(opts.get("profile-b")) : exampleProfile("b");
        int rounds = Preference.positiveInt(new BigInteger(opts.getOrDefault("rounds", "30")), "rounds");
        int sample = Preference.positiveInt(new BigInteger(opts.getOrDefault("sample-size", "4096")), "sample_size");
        BigInteger seed = new BigInteger(opts.getOrDefault("seed", "0"));
        Map<String, Object> report = negotiate(a, b, rounds, seed, opts.getOrDefault("search-mode", "auto"), sample);
        String output = opts.getOrDefault("output", "outputs/java-demo.json");
        write(output, report);
        System.out.println("Outcome: " + report.get("outcome") + " | turns: " + ((List<?>)report.get("trace")).size());
        System.out.println("Trace: " + output);
    }
    public static Map<String, Object> negotiate(Preference a, Preference b, int rounds, BigInteger seed, String mode, int sample) {
        if (rounds < 1 || rounds > Integer.MAX_VALUE / 2) throw new IllegalArgumentException("rounds must be a positive bounded integer");
        if (!a.domain.equals(b.domain)) throw new IllegalArgumentException("Both profiles must describe the same ordered domain");
        CBOMAgent[] agents = {
            new CBOMAgent(a, Json.map("mode", mode, "seed", seed, "sample_size", sample)),
            new CBOMAgent(b, Json.map("mode", mode, "seed", seed.add(BigInteger.ONE), "sample_size", sample))
        };
        List<Object> trace = new ArrayList<>();
        String outcome = "deadline";
        Map<String, String> agreement = null;
        for (int turn = 0; turn < 2 * rounds; turn++) {
            int side = turn % 2;
            double t = (double)turn / Math.max(1, 2 * rounds - 1);
            CBOMAgent.Action action = agents[side].act(t);
            Map<String, Object> record = Json.map("turn", turn + 1, "agent", side == 0 ? "A" : "B", "time", t);
            record.putAll(action.toMap()); record.put("model_observations", agents[side].model.observations()); trace.add(record);
            if (action.kind().equals("accept")) { outcome = "agreement"; agreement = action.bid(); break; }
            if (action.kind().equals("end")) { outcome = "ended"; break; }
            agents[1 - side].receive(action.bid(), t);
        }
        return Json.map("software_version", VERSION, "kind", "synthetic demonstration",
                "settings", Json.map("rounds", rounds, "seed", seed, "search_mode", mode, "sample_size", sample),
                "profiles", Json.map("A", a.toMap(), "B", b.toMap()), "outcome", outcome, "agreement", agreement,
                "utilities", agreement == null ? null : Json.map("A", a.utility(agreement), "B", b.utility(agreement)), "trace", trace);
    }
    private static void learn(Map<String, String> opts) throws IOException {
        checkOptions(opts, Set.of("profile", "offers", "history-size", "output"));
        if (!opts.containsKey("offers")) throw new IllegalArgumentException("Missing required --offers");
        ConflictBasedOpponentModel model = new ConflictBasedOpponentModel(readProfile(opts.get("profile")),
                Preference.positiveInt(new BigInteger(opts.getOrDefault("history-size", "1000")), "history_size"));
        try (BufferedReader reader = Files.newBufferedReader(Path.of(opts.get("offers")), StandardCharsets.UTF_8)) {
            String line; int number = 0;
            while ((line = reader.readLine()) != null) {
                number++;
                if (line.isBlank()) continue;
                try { model.update(Json.object(Json.parse(line))); }
                catch (IllegalArgumentException error) { throw new IllegalArgumentException("Invalid offer at line " + number + ": " + error.getMessage()); }
            }
        }
        String output = opts.getOrDefault("output", "outputs/java-estimated-profile.json");
        write(output, model.preference().toMap());
        System.out.println("Offers: " + model.observations() + " | comparisons: " + model.comparisons() + " | evidence cells: " + model.evidenceCells());
        System.out.println("Estimated profile: " + output);
    }
    private static void serve() throws IOException {
        CBOMAgent agent = null;
        BufferedReader input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        PrintWriter output = new PrintWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8), true);
        String line;
        while ((line = input.readLine()) != null) {
            try {
                Map<String, Object> request = Json.object(Json.parse(line));
                Object operation = request.get("op");
                if (!(operation instanceof String op)) throw new IllegalArgumentException("Request requires string op");
                if (op.equals("close")) { output.println(Json.stringify(Json.map("ok", true, "result", null))); return; }
                Object result;
                if (op.equals("init")) {
                    Map<String, Object> opts = request.containsKey("options") ? Json.object(request.get("options")) : Map.of();
                    // Construct first: failed reinitialization preserves the previous session.
                    agent = new CBOMAgent(Preference.fromMap(request.get("profile")), opts);
                    result = agent.model.state();
                } else {
                    if (agent == null) throw new IllegalStateException("Initialize an agent first");
                    switch (op) {
                        case "receive" -> {
                            double t = Preference.unit(request.get("t"), "Normalized time");
                            agent.receive(Json.object(request.get("bid")), t); result = agent.model.state();
                        }
                        case "act" -> result = agent.act(Preference.unit(request.get("t"), "Normalized time")).toMap();
                        case "inspect" -> result = agent.model.state();
                        default -> throw new IllegalArgumentException("Unknown operation: " + op);
                    }
                }
                Map<String, Object> response = Json.map("ok", true, "result", result);
                if (op.equals("act")) response.put("action", result);
                output.println(Json.stringify(response));
            } catch (IllegalArgumentException | IllegalStateException | ArithmeticException error) {
                output.println(Json.stringify(Json.map("ok", false, "error", error.getMessage(), "error_type", error.getClass().getSimpleName())));
            }
        }
    }
}
