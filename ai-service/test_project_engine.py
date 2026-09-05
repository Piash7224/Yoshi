from pathlib import Path

import pytest

from project_engine import (
    ProjectError,
    build_memory,
    commit_evidence,
    documentation_status,
    get_changed_files,
    get_commit_diff,
    get_current_branch,
    get_dependencies,
    get_git_status,
    get_project_structure,
    project_profile,
    readiness_audit,
    recent_commits,
    repository_info,
    retrieve,
)
from test_manual import get_commit_diff as get_manual_commit_diff


REPO = str(Path(__file__).resolve().parents[1])


def test_repository_facts_and_history():
    info = repository_info(REPO)
    assert info["name"] == "Yoshi"
    assert len(info["head"]) == 40
    assert recent_commits(REPO, 2)
    assert commit_evidence(REPO)["hash"] == info["head"]
    assert get_current_branch(REPO)
    assert isinstance(get_git_status(REPO)["entries"], list)


def test_profile_and_audits_are_deterministic():
    profile = project_profile(REPO)
    assert "README.md" in profile["documentation"]
    assert profile["file_count"] > 5
    assert 0 <= readiness_audit(REPO)["score"] <= 100
    assert "suggestions" in documentation_status(REPO)


def test_local_memory_indexes_and_retrieves_project_content():
    result = build_memory(REPO)
    assert result["chunks_indexed"] > 0
    matches = retrieve(REPO, "Ollama structured commit analysis")
    assert matches
    assert all("source" in match and "content" in match for match in matches)


def test_non_repository_is_rejected(tmp_path):
    with pytest.raises(ProjectError):
        repository_info(str(tmp_path))


def test_manual_commit_extraction_is_repository_root_relative(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parent)
    diff, _, stat = get_manual_commit_diff("2ad4021")
    assert "backend/package.json" in diff
    assert "backend/server.js" in diff
    assert "package-lock.json" not in diff
    assert "package-lock.json" not in stat


def test_repository_subdirectory_resolves_to_root():
    info = repository_info(str(Path(REPO) / "ai-service"))
    assert Path(info["path"]) == Path(REPO)


def test_status_preserves_dotfile_paths():
    paths = {item["path"] for item in get_git_status(REPO)["entries"]}
    assert ".gitignore" in paths


def test_changed_files_and_diff_are_structured():
    files = get_changed_files(REPO, "2ad4021")
    assert {item["path"] for item in files} >= {"backend/package.json", "backend/server.js"}
    diff = get_commit_diff(REPO, "2ad4021")
    assert "backend/server.js" in diff
    assert "package-lock.json" not in diff


def test_dependencies_and_structure_are_discoverable():
    result = get_dependencies(REPO)
    names = {item.get("name") for item in result["dependencies"]}
    assert "fastapi" in names
    assert "ollama" in names
    assert "express" in names
    structure = get_project_structure(REPO)
    assert "ai-service" in structure["tree"]
    assert "backend" in structure["tree"]
    assert "__files__" not in structure["directories"]
