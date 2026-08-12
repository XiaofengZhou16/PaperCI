"""Install one PaperCI distribution in a clean environment and exercise the CLI."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(str(part) for part in command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def environment_python(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("distribution", type=Path)
    args = parser.parse_args()

    distribution = args.distribution.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="paperci-dist-") as temporary_directory:
        root = Path(temporary_directory)
        environment = root / "venv"
        project = root / "demo"

        run([sys.executable, "-m", "venv", str(environment)])
        python = environment_python(environment)
        run([str(python), "-m", "pip", "install", str(distribution)])
        run([str(python), "-m", "pip", "check"])
        run([str(python), "-m", "paperci", "--version"])
        run([str(python), "-m", "paperci", "demo", str(project)])
        run([str(python), "-m", "paperci", "doctor", str(project)])
        run([str(python), "-m", "paperci", "lint", str(project), "--fail-on", "never"])
        run([str(python), "-m", "paperci", "compare", str(project)])
        run([str(python), "-m", "paperci", "compare-hypotheses", str(project)])


if __name__ == "__main__":
    main()
