#!/usr/bin/env python3
"""Compile the standalone Java implementation using only a JDK and Python."""
import shutil
import subprocess
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    javac = shutil.which("javac")
    jar = shutil.which("jar")
    if not javac or not jar:
        raise SystemExit("JDK 17 or newer is required; put javac and jar on PATH.")
    classes = root / "build" / "classes"
    if classes.exists():
        shutil.rmtree(classes)
    classes.mkdir(parents=True, exist_ok=True)
    sources = sorted((root / "src").rglob("*.java"))
    subprocess.run([javac, "--release", "17", "-encoding", "UTF-8", "-d", str(classes),
                    *map(str, sources)], check=True)
    shutil.copytree(root / "data", classes / "data", dirs_exist_ok=True)
    metadata = classes / "META-INF"
    metadata.mkdir(exist_ok=True)
    for name in ("LICENSE", "NOTICE", "PSF-LICENSE"):
        shutil.copyfile(root / name, metadata / name)
    destination = root / "build" / "cbom.jar"
    subprocess.run([jar, "--create", "--file", str(destination), "--main-class", "org.cbom.Main",
                    "-C", str(classes), "."], check=True)
    print(destination)


if __name__ == "__main__":
    main()
