"""
Quick manual test — no pytest needed yet.

Usage:
    python test_manual.py <commit-hash>

Run from inside any git repo. It pulls the real diff for that commit
and sends it through analyze_commit(), so you can eyeball whether the
model's classification actually makes sense.
"""

import subprocess
import sys
from pathlib import Path

from llm_service import analyze_commit


# Lockfiles and similar generated files add huge token counts with
# basically zero semantic signal for "what changed and why" — excluding
# them keeps the diff small and relevant.
NOISY_FILE_PATTERNS = [
    ":(exclude)**/package-lock.json",
    ":(exclude)**/yarn.lock",
    ":(exclude)**/pnpm-lock.yaml",
]


def get_commit_diff(commit_hash: str) -> tuple[str, str, str]:
    repo_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    ).stdout.strip()

    git = ["git", "-C", repo_root]
    message = subprocess.run(
        [*git, "log", "-1", "--pretty=%B", commit_hash],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    ).stdout.strip()

    stat_summary = subprocess.run(
        [*git, "show", commit_hash, "--stat", "--pretty=format:", "--", ".", *NOISY_FILE_PATTERNS],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    ).stdout.strip()

    diff = subprocess.run(
        [*git, "show", commit_hash, "--pretty=format:", "--", ".", *NOISY_FILE_PATTERNS],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True,
    ).stdout.strip()

    if not diff:
        raise ValueError(
            "This commit has no analyzable text diff after generated files were excluded."
        )

    return diff, message, stat_summary


def get_commit_context(commit_hash: str, diff: str, max_chars: int = 8000) -> str:
    repo_root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=True,
    ).stdout.strip()
    paths = []
    for line in diff.splitlines():
        if line.startswith("diff --git a/"):
            paths.append(line.split(" b/", 1)[1])
    sections = []
    for path in paths:
        if Path(path).suffix.lower() not in {".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".txt", ".md", ".toml", ".yaml", ".yml"}:
            continue
        result = subprocess.run(
            ["git", "-C", repo_root, "show", f"{commit_hash}:{path}"],
            capture_output=True, check=False,
        )
        if result.returncode:
            continue
        raw = result.stdout
        if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
            content = raw.decode("utf-16", errors="replace")
        else:
            content = raw.decode("utf-8-sig", errors="replace")
        sections.append(f"FILE: {path}\n{content[:3000]}")
    return "\n\n".join(sections)[:max_chars]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_manual.py <commit-hash>")
        sys.exit(1)

    commit_hash = sys.argv[1]
    diff, message, stat_summary = get_commit_diff(commit_hash)
    project_context = get_commit_context(commit_hash, diff)

    print(f"Commit message: {message}\n")
    print(f"--- Stat summary ---\n{stat_summary}\n")
    result = analyze_commit(
        diff, message, stat_summary=stat_summary, project_context=project_context
    )

    print("--- Analysis ---")
    print(result.model_dump_json(indent=2))
