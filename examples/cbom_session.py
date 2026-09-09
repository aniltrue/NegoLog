"""Run a Python/Java CBOM session from a clean NegoLog checkout."""

import argparse
from pathlib import Path
import sys

# A checked-out repository is the supported NegoLog installation layout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents import BoulwareAgent, CBOMAgent, CBOMJavaAgent, ConcederAgent
from nenv import SessionManager


def main():
    choices = {"python": CBOMAgent, "java": CBOMJavaAgent,
               "boulware": BoulwareAgent, "conceder": ConcederAgent}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-a", choices=choices, default="python")
    parser.add_argument("--agent-b", choices=choices, default="conceder")
    parser.add_argument("--domain", default="0")
    parser.add_argument("--rounds", type=int, default=30)
    parser.add_argument("--output", type=Path, default=Path("results/cbom-session.xlsx"))
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("--rounds must be positive")
    # domain_loader currently resolves the repository's domains/ from cwd.
    # State that contract clearly instead of silently changing process cwd.
    if not Path("domains").is_dir():
        parser.error("Run this command from the NegoLog repository root")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    manager = SessionManager(choices[args.agent_a], choices[args.agent_b], args.domain,
                             None, args.rounds, [], [])
    result = manager.run(str(args.output))["TournamentResults"]
    print(f"{result['AgentA']} vs {result['AgentB']}: {result['Result']}")
    print(f"Utility A: {result['AgentAUtility']:.3f} | Utility B: {result['AgentBUtility']:.3f}")
    if "EndReason" in result:
        print(f"End reason: {result['EndReason']}")
    print(f"Session workbook: {args.output}")
    return 1 if result["Result"] in ("Error", "TimedOut") else 0


if __name__ == "__main__":
    raise SystemExit(main())
