"""Deterministic repository intelligence used by the AI-facing workflows."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import tomllib
from collections import Counter
from pathlib import Path

from llm_service import MODEL_NAME

IGNORED_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}
TEXT_SUFFIXES = {".md", ".txt", ".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".yaml", ".yml", ".toml"}
SECRET_RE = re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}")
WORD_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]{2,}")
MEMORY_DIR = Path(__file__).resolve().parent / "data" / "memory"


class ProjectError(ValueError):
    pass


def _repo(path: str) -> Path:
    candidate = Path(path).expanduser().resolve()
    if not candidate.is_dir():
        raise ProjectError("path must be an existing directory inside a Git repository")
    result = subprocess.run(
        ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
    )
    if result.returncode:
        raise ProjectError("path must be an existing directory inside a Git repository")
    return Path(result.stdout.strip()).resolve()


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30
    )
    if result.returncode:
        raise ProjectError(result.stderr.strip() or "git command failed")
    return result.stdout.rstrip()


def _git_file_at_commit(repo: Path, commit: str, path: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"],
        capture_output=True, timeout=30,
    )
    if result.returncode:
        return ""
    if result.stdout.startswith((b"\xff\xfe", b"\xfe\xff")):
        return result.stdout.decode("utf-16", errors="replace")
    return result.stdout.decode("utf-8-sig", errors="replace")


def repository_info(path: str) -> dict:
    repo = _repo(path)
    remote = _git(repo, "remote", "get-url", "origin") if _git(repo, "remote") else ""
    branch = get_current_branch(path)
    status = get_git_status(path)
    return {
        "path": str(repo),
        "name": repo.name,
        "branch": branch,
        "is_detached": not bool(_git(repo, "branch", "--show-current")),
        "is_dirty": status["is_dirty"],
        "status": status["entries"],
        "remote": remote,
        "head": _git(repo, "rev-parse", "HEAD"),
        "commit_count": int(_git(repo, "rev-list", "--count", "HEAD")),
    }


def get_current_branch(path: str) -> str:
    repo = _repo(path)
    branch = _git(repo, "branch", "--show-current")
    return branch or f"detached@{_git(repo, 'rev-parse', '--short', 'HEAD')}"


def get_git_status(path: str) -> dict:
    repo = _repo(path)
    raw = _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    entries = []
    for line in raw.splitlines():
        if len(line) < 3:
            continue
        index_status, worktree_status, file_path = line[0], line[1], line[3:]
        old_path = None
        if " -> " in file_path:
            old_path, file_path = file_path.split(" -> ", 1)
        entries.append({
            "path": file_path, "old_path": old_path,
            "index_status": index_status, "worktree_status": worktree_status,
            "staged": index_status not in {" ", "?"},
            "untracked": index_status == "?" and worktree_status == "?",
        })
    return {"is_dirty": bool(entries), "entries": entries, "count": len(entries)}


def recent_commits(path: str, limit: int = 20) -> list[dict]:
    repo = _repo(path)
    raw = _git(repo, "log", f"-{min(max(limit, 1), 100)}", "--pretty=%H%x1f%h%x1f%an%x1f%aI%x1f%s")
    return [dict(zip(("hash", "short_hash", "author", "date", "message"), line.split("\x1f"))) for line in raw.splitlines() if line]


def get_changed_files(path: str, commit: str = "HEAD") -> list[dict]:
    repo = _repo(path)
    commit_hash = _git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}")
    raw = _git(repo, "show", "--format=", "--name-status", "--find-renames", commit_hash)
    files = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        code = parts[0]
        entry = {"status": code[0], "path": parts[-1], "old_path": parts[1] if code.startswith(("R", "C")) and len(parts) > 2 else None}
        files.append(entry)
    return files


def get_commit_diff(path: str, commit: str = "HEAD") -> str:
    repo = _repo(path)
    commit_hash = _git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}")
    return _git(
        repo, "show", "--format=", "--no-ext-diff", commit_hash, "--", ".",
        ":(exclude)**/package-lock.json", ":(exclude)**/yarn.lock", ":(exclude)**/pnpm-lock.yaml",
    )


def commit_evidence(path: str, commit: str = "HEAD") -> dict:
    repo = _repo(path)
    commit_hash = _git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}")
    changed_file_entries = get_changed_files(path, commit_hash)
    changed_files = [entry["path"] for entry in changed_file_entries]
    context_sections = []
    for name in changed_files:
        if Path(name).suffix.lower() in TEXT_SUFFIXES:
            content = _git_file_at_commit(repo, commit_hash, name)
            if content:
                context_sections.append(f"FILE: {name}\n{content[:3000]}")
    return {
        "hash": commit_hash,
        "message": _git(repo, "log", "-1", "--pretty=%B", commit_hash),
        "changed_files": changed_files,
        "changed_file_entries": changed_file_entries,
        "stat_summary": _git(repo, "show", "--stat", "--pretty=format:", commit_hash),
        "diff": get_commit_diff(path, commit_hash),
        "project_context": "\n\n".join(context_sections)[:8000],
    }


def project_files(path: str, limit: int = 1000) -> list[str]:
    repo = _repo(path)
    files = []
    for item in repo.rglob("*"):
        if item.is_file() and not any(part in IGNORED_DIRS for part in item.relative_to(repo).parts):
            files.append(item.relative_to(repo).as_posix())
            if len(files) >= limit:
                break
    return sorted(files)


def get_project_structure(path: str, limit: int = 2000) -> dict:
    files = project_files(path, limit)
    root: dict = {}
    for file_path in files:
        node = root
        parts = file_path.split("/")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node.setdefault("__files__", []).append(parts[-1])
    return {
        "tree": root,
        "directories": sorted(key for key in root if key != "__files__"),
        "root_files": sorted(root.get("__files__", [])),
        "files": files,
        "file_count": len(files),
        "truncated": len(files) >= limit,
    }


def _read_project_text(file: Path) -> str:
    raw = file.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def get_dependencies(path: str) -> dict:
    repo = _repo(path)
    manifests = []
    dependencies = []
    for relative in project_files(path, 3000):
        file = repo / relative
        name = file.name.lower()
        try:
            if name == "package.json":
                data = json.loads(_read_project_text(file))
                manifests.append(relative)
                for group in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                    for dependency, version in data.get(group, {}).items():
                        dependencies.append({"name": dependency, "version": str(version), "scope": group, "ecosystem": "npm", "manifest": relative})
            elif name.startswith("requirements") and name.endswith(".txt"):
                manifests.append(relative)
                for line in _read_project_text(file).splitlines():
                    line = line.strip()
                    if not line or line.startswith(("#", "-r", "--")):
                        continue
                    match = re.match(r"([A-Za-z0-9_.-]+)\s*([<>=!~].+)?", line)
                    if match:
                        dependencies.append({"name": match.group(1), "version": (match.group(2) or "").strip(), "scope": "runtime", "ecosystem": "python", "manifest": relative})
            elif name == "pyproject.toml":
                manifests.append(relative)
                data = tomllib.loads(_read_project_text(file))
                for item in data.get("project", {}).get("dependencies", []):
                    match = re.match(r"([A-Za-z0-9_.-]+)\s*(.*)", item)
                    if match:
                        dependencies.append({"name": match.group(1), "version": match.group(2), "scope": "runtime", "ecosystem": "python", "manifest": relative})
        except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
            manifests.append(relative)
            dependencies.append({"manifest": relative, "error": str(exc), "ecosystem": "unknown"})
    return {"manifests": sorted(set(manifests)), "dependencies": dependencies, "count": len([item for item in dependencies if "name" in item])}


def project_profile(path: str) -> dict:
    repo = _repo(path)
    files = project_files(path)
    extensions = Counter(Path(name).suffix.lower() or "[none]" for name in files)
    manifests = [name for name in files if Path(name).name in {"package.json", "requirements.txt", "pyproject.toml", "Cargo.toml", "go.mod"}]
    docs = [name for name in files if Path(name).suffix.lower() == ".md"]
    return {
        **repository_info(path),
        "file_count": len(files),
        "languages": extensions.most_common(10),
        "manifests": manifests,
        "documentation": docs,
        "top_level": sorted({name.split("/", 1)[0] for name in files}),
    }


def readiness_audit(path: str) -> dict:
    repo = _repo(path)
    files = project_files(path)
    lower = {name.lower() for name in files}
    checks = {
        "readme": "readme.md" in lower,
        "license": any(name.startswith("license") for name in lower),
        "gitignore": ".gitignore" in lower,
        "installation_docs": any("install" in name or "getting-started" in name for name in lower),
        "tests": any("test" in Path(name).name.lower() for name in files),
        "dependency_manifest": any(Path(name).name in {"package.json", "requirements.txt", "pyproject.toml"} for name in files),
        "ci": any(name.startswith(".github/workflows/") for name in lower),
    }
    secret_hits = []
    for name in files:
        file = repo / name
        if file.suffix.lower() not in TEXT_SUFFIXES or file.stat().st_size > 250_000:
            continue
        try:
            if SECRET_RE.search(file.read_text(encoding="utf-8", errors="ignore")):
                secret_hits.append(name)
        except OSError:
            pass
    checks["no_obvious_secrets"] = not secret_hits
    score = round(100 * sum(checks.values()) / len(checks))
    return {"score": score, "checks": checks, "secret_findings": secret_hits, "ready": score >= 80 and not secret_hits}


def _chunks(path: str) -> list[dict]:
    repo = _repo(path)
    chunks = []
    for name in project_files(path, 500):
        file = repo / name
        if file.suffix.lower() not in TEXT_SUFFIXES or file.stat().st_size > 300_000:
            continue
        text = file.read_text(encoding="utf-8", errors="ignore")
        for index in range(0, len(text), 1800):
            content = text[index:index + 2200].strip()
            if content:
                chunks.append({"id": hashlib.sha1(f"{name}:{index}".encode()).hexdigest(), "source": name, "content": content})
    return chunks


def build_memory(path: str) -> dict:
    repo = _repo(path)
    chunks = _chunks(path)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    target = MEMORY_DIR / f"{hashlib.sha1(str(repo).encode()).hexdigest()}.json"
    target.write_text(json.dumps({"repo": str(repo), "chunks": chunks}), encoding="utf-8")
    return {"chunks_indexed": len(chunks), "index": str(target)}


def retrieve(path: str, question: str, limit: int = 5) -> list[dict]:
    repo = _repo(path)
    target = MEMORY_DIR / f"{hashlib.sha1(str(repo).encode()).hexdigest()}.json"
    if not target.exists():
        build_memory(path)
    chunks = json.loads(target.read_text(encoding="utf-8"))["chunks"]
    query = Counter(word.lower() for word in WORD_RE.findall(question))
    scored = []
    for chunk in chunks:
        words = Counter(word.lower() for word in WORD_RE.findall(chunk["content"]))
        score = sum(query[word] * words[word] for word in query) / math.sqrt(max(sum(words.values()), 1))
        if score:
            scored.append((score, chunk))
    return [{**chunk, "score": round(score, 4)} for score, chunk in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


def documentation_status(path: str) -> dict:
    profile = project_profile(path)
    audit = readiness_audit(path)
    suggestions = []
    if not audit["checks"]["readme"]:
        suggestions.append("Add a README with purpose, setup, and usage.")
    if not audit["checks"]["installation_docs"]:
        suggestions.append("Add installation or getting-started documentation.")
    if not any("architecture" in name.lower() for name in profile["documentation"]):
        suggestions.append("Document the project architecture.")
    return {"files": profile["documentation"], "suggestions": suggestions, "up_to_date": not suggestions}


def agent_plan(path: str, goal: str) -> dict:
    """Create a safe read-only plan. Execution is deliberately approval-gated."""
    audit = readiness_audit(path)
    docs = documentation_status(path)
    steps = [f"Inspect repository for goal: {goal}"]
    steps.extend(f"Propose fix: {suggestion}" for suggestion in docs["suggestions"])
    steps.extend(f"Review failed readiness check: {name}" for name, ok in audit["checks"].items() if not ok)
    steps.append("Request explicit approval before modifying project files")
    return {"goal": goal, "steps": list(dict.fromkeys(steps)), "requires_approval": True, "executed": False}
