"""Small local negotiation and opponent-model command-line tools."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from importlib.resources import files
from pathlib import Path

from . import __version__
from .model import ConflictBasedOpponentModel
from .preferences import Preference
from .strategy import CBOMAgent


def example_profile(side: str) -> Preference:
    """Read a packaged synthetic profile, independent of the current directory."""
    return Preference.from_dict(json.loads(files("cbom").joinpath(f"data/profile_{side}.json").read_text()))


def negotiate(profile_a: Preference, profile_b: Preference, rounds: int = 30,
              seed: int = 0, mode: str = "auto", sample_size: int = 4096) -> dict:
    """Run a deterministic local alternating-offers example with two CBOM agents."""
    if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 1:
        raise ValueError("rounds must be a positive integer")
    if dict(profile_a.domain) != dict(profile_b.domain):
        raise ValueError("Both profiles must describe the same ordered domain")
    profiles = [profile_a, profile_b]
    agents = [CBOMAgent(p, seed=seed + i, mode=mode, sample_size=sample_size) for i, p in enumerate(profiles)]
    trace = []
    outcome = "deadline"
    agreement = None
    for turn in range(2 * rounds):
        side = turn % 2
        t = turn / max(1, 2 * rounds - 1)
        action = agents[side].act(t)
        record = {"turn": turn + 1, "agent": "AB"[side], "time": t,
                  **asdict(action), "model_observations": agents[side].model.observations}
        trace.append(record)
        if action.kind == "accept":
            outcome = "agreement"
            agreement = action.bid
            break
        if action.kind == "end":
            outcome = "ended"
            break
        agents[1 - side].receive(action.bid, t)
    return {"software_version": __version__, "kind": "synthetic demonstration",
            "settings": {"rounds": rounds, "seed": seed, "search_mode": mode, "sample_size": sample_size},
            "profiles": {"A": profile_a.to_dict(), "B": profile_b.to_dict()},
            "outcome": outcome, "agreement": agreement,
            "utilities": ({"A": profile_a.utility(agreement), "B": profile_b.utility(agreement)}
                          if agreement else None), "trace": trace}


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CBOM: learn opponent preferences and run local negotiations")
    parser.add_argument("--version", action="version", version=f"CBOM {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Run two CBOM agents on synthetic or user-supplied profiles")
    demo.add_argument("--profile-a", type=Path)
    demo.add_argument("--profile-b", type=Path)
    demo.add_argument("--rounds", type=int, default=30)
    demo.add_argument("--seed", type=int, default=0)
    demo.add_argument("--search-mode", choices=["auto", "exact", "sampled"], default="auto")
    demo.add_argument("--sample-size", type=int, default=4096)
    demo.add_argument("--output", type=Path, default=Path("outputs/demo.json"))
    learn = commands.add_parser("learn", help="Estimate preferences from JSONL opponent offers")
    learn.add_argument("--profile", type=Path, required=True, help="Your own utility profile")
    learn.add_argument("--offers", type=Path, required=True, help="One complete JSON bid per line")
    learn.add_argument("--history-size", type=int, default=1000)
    learn.add_argument("--output", type=Path, default=Path("outputs/estimated-profile.json"))
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            if bool(args.profile_a) != bool(args.profile_b):
                parser.error("Provide both --profile-a and --profile-b, or neither")
            profile_a = Preference.from_json(args.profile_a) if args.profile_a else example_profile("a")
            profile_b = Preference.from_json(args.profile_b) if args.profile_b else example_profile("b")
            report = negotiate(profile_a, profile_b, args.rounds, args.seed, args.search_mode, args.sample_size)
            write_json(args.output, report)
            print(f"Outcome: {report['outcome']} | turns: {len(report['trace'])}")
            if report["utilities"]:
                print(f"Utility A: {report['utilities']['A']:.3f} | Utility B: {report['utilities']['B']:.3f}")
            print(f"Trace: {args.output}")
        else:
            model = ConflictBasedOpponentModel(Preference.from_json(args.profile), args.history_size)
            with args.offers.open(encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, 1):
                    if not line.strip():
                        continue
                    try:
                        model.update(json.loads(line))
                    except (ValueError, TypeError) as error:
                        raise ValueError(f"Invalid offer at line {line_number}: {error}") from error
            write_json(args.output, model.preference.to_dict())
            print(f"Offers: {model.observations} | comparisons: {model.comparisons} | evidence cells: {model.evidence_cells}")
            print(f"Estimated profile: {args.output}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
