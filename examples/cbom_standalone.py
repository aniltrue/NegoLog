"""Use the bundled standalone CBOM CLI without importing NegoLog or a JVM."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agents/CBOM/_vendor"))

from cbom.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
