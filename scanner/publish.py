"""Publish generated public reports without exposing the history database or source branch."""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path


def publish_report(repository: Path, output: Path) -> str:
    def git(*args: str, data: str | None = None, environment: dict | None = None) -> str:
        result = subprocess.run(["git", *args], cwd=repository, input=data, text=True,
                                capture_output=True, env=environment, check=True)
        return result.stdout.strip()

    files = {name: output / name for name in ("report.json", "index.html")}
    if not all(path.is_file() for path in files.values()):
        raise ValueError("Complete generated report required; refusing to publish partial results")
    branch = "scanner-report"
    remote = subprocess.run(["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
                            cwd=repository, capture_output=True, text=True)
    if remote.returncode not in (0, 2):
        raise RuntimeError("Could not inspect remote report branch")
    parent = None
    if remote.returncode == 0:
        git("fetch", "--no-tags", "--depth=1", "origin", branch)
        parent = git("rev-parse", "FETCH_HEAD")
    with tempfile.TemporaryDirectory(prefix="market-report-") as directory:
        environment = os.environ.copy()
        environment["GIT_INDEX_FILE"] = str(Path(directory) / "index")
        git("read-tree", "--empty", environment=environment)
        for name, path in files.items():
            blob = git("hash-object", "-w", str(path.resolve()))
            git("update-index", "--add", "--cacheinfo", f"100644,{blob},{name}", environment=environment)
        tree = git("write-tree", environment=environment)
    if parent and tree == git("rev-parse", f"{parent}^{{tree}}"):
        return "Report unchanged"
    args = ["-c", "user.name=market-scanner[bot]", "-c",
            "user.email=market-scanner@users.noreply.github.com", "commit-tree", tree]
    if parent:
        args.extend(["-p", parent])
    commit = git(*args, data="Publish current market report\n")
    # Normal fast-forward push: concurrent changes fail rather than overwrite.
    git("push", "origin", f"{commit}:refs/heads/{branch}")
    return commit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("output/live"))
    args = parser.parse_args()
    print(publish_report(Path.cwd(), args.output))


if __name__ == "__main__":
    main()
