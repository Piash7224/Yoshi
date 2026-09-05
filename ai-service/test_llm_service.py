import json
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from llm_service import MAX_DIFF_CHARS, analyze_commit, build_prompt, extract_change_facts, prepare_diff, truncate_diff
from main import app


VALID_RESPONSE = {
    "summary": "Added validation for blank project names.",
    "changed_components": ["projects.py"],
    "change_type": "bugfix",
    "risk_level": "low",
    "reasoning": "The validation is isolated to project input handling.",
    "evidence": ["+ reject blank names"],
}


def test_valid_model_output_is_parsed():
    with patch("llm_service._call_ollama", return_value=json.dumps(VALID_RESPONSE)):
        result = analyze_commit("+ reject blank names", "fix: validate names")
    assert result.change_type == "bugfix"
    assert result.changed_components == []


def test_known_change_type_alias_is_normalized():
    response = {**VALID_RESPONSE, "change_type": "feat", "evidence": ["+ add project creation"]}
    with patch("llm_service._call_ollama", return_value=json.dumps(response)):
        result = analyze_commit("+ add project creation", "feat: projects")
    assert result.change_type == "feature"


def test_invalid_output_retries_then_returns_marked_fallback():
    with patch("llm_service._call_ollama", return_value='{"unexpected": true}') as call:
        result = analyze_commit("+ change", "unknown change")
    assert call.call_count == 2
    assert result.summary == "Automated analysis could not be grounded in the supplied diff."


def test_diff_is_bounded():
    result = truncate_diff("x" * (MAX_DIFF_CHARS + 1000))
    assert len(result) <= MAX_DIFF_CHARS
    assert "TRUNCATED:" in result


def test_prompt_has_grounding_rules_without_unrelated_example():
    prompt = build_prompt(
        "+def validate_email(email):\n+    return '@' in email",
        "feat: add email validation",
        stat_summary="app.py | 2 ++",
    )
    assert "source of truth" in prompt
    assert "If the evidence is insufficient" in prompt
    assert "signup form" not in prompt
    assert "shared state" not in prompt


def test_empty_model_components_are_filled_from_diff_headers():
    response = {**VALID_RESPONSE, "changed_components": [], "evidence": ["+def validate_email(email):"]}
    diff = "--- a/app.py\n+++ b/app.py\n+def validate_email(email):\n+    return '@' in email"
    with patch("llm_service._call_ollama", return_value=json.dumps(response)):
        result = analyze_commit(diff, "feat: add email validation")
    assert result.changed_components == ["app.py"]


def test_unsupported_model_evidence_is_replaced_deterministically():
    response = {**VALID_RESPONSE, "evidence": ["+ invented behavior"]}
    with patch("llm_service._call_ollama", return_value=json.dumps(response)) as call:
        result = analyze_commit("+ actual behavior", "feature")
    assert call.call_count == 1
    assert result.evidence == ["+ actual behavior"]


def test_large_multifile_diff_keeps_multiple_file_sections():
    first = "diff --git a/one.py b/one.py\n--- a/one.py\n+++ b/one.py\n" + "+a\n" * 7000
    second = "diff --git a/two.py b/two.py\n--- a/two.py\n+++ b/two.py\n" + "+b\n" * 7000
    context = prepare_diff(first + second, 2000)
    assert "one.py" in context.text
    assert "two.py" in context.text
    assert context.partial


def test_empty_diff_skips_model_instead_of_guessing():
    with patch("llm_service._call_ollama") as call:
        result = analyze_commit("", "feat: claim without evidence", "1 file changed")
    call.assert_not_called()
    assert result.summary == "No analyzable diff was supplied."
    assert result.evidence == []


def test_binary_file_is_component_and_marks_scope_partial():
    response = {**VALID_RESPONSE, "summary": "Added FastAPI service initialization"}
    diff = "diff --git a/main.py b/main.py\n--- a/main.py\n+++ b/main.py\n+from fastapi import FastAPI\ndiff --git a/requirements.txt b/requirements.txt\nBinary files a/requirements.txt and b/requirements.txt differ"
    with patch("llm_service._call_ollama", return_value=json.dumps(response)):
        result = analyze_commit(diff, "chore: initialize service", "requirements.txt | Bin 0 -> 540 bytes")
    assert result.changed_components == ["main.py", "requirements.txt"]
    assert result.analysis_scope == "partial"
    assert "requirements.txt" in result.limitations[0]


def test_deterministic_facts_find_dependencies_scripts_and_routes():
    diff = '''diff --git a/package.json b/package.json
--- a/package.json
+++ b/package.json
+    "dev": "nodemon server.js",
+    "nodemon": "^3.1.0"
diff --git a/server.js b/server.js
--- a/server.js
+++ b/server.js
+const mongoose = require("mongoose")
+app.get("/health", handler)
'''
    facts = extract_change_facts(diff)
    assert facts["added_scripts"]
    assert facts["added_dependency_lines"]
    assert facts["added_routes"]


def test_dependency_manifest_and_dotenv_trigger_documentation_topics():
    response = {
        **VALID_RESPONSE,
        "summary": "Initialized the FastAPI service and environment loading",
        "reasoning": "FastAPI setup now loads environment variables through dotenv.",
    }
    diff = "diff --git a/main.py b/main.py\n--- /dev/null\n+++ b/main.py\n+from dotenv import load_dotenv\n+load_dotenv()\ndiff --git a/requirements.txt b/requirements.txt\nBinary files /dev/null and b/requirements.txt differ"
    stat = "main.py | 2 ++\nrequirements.txt | Bin 0 -> 100 bytes"
    with patch("llm_service._call_ollama", return_value=json.dumps(response)):
        result = analyze_commit(diff, "chore: initialize service", stat)
    assert "dependencies" in result.documentation_topics
    assert "configuration and database setup" in result.documentation_topics


def test_endpoint_rejects_blank_diff():
    response = TestClient(app).post(
        "/analyze-commit", json={"diff": "   ", "commit_message": "test"}
    )
    assert response.status_code == 422


def test_endpoint_passes_stat_summary():
    with patch("main.analyze_commit", return_value=VALID_RESPONSE) as analyze:
        response = TestClient(app).post(
            "/analyze-commit",
            json={"diff": "+ change", "commit_message": "test", "stat_summary": "1 file"},
        )
    assert response.status_code == 200
    analyze.assert_called_once_with(
        "+ change", "test", stat_summary="1 file", project_context=""
    )


def test_prompt_includes_targeted_project_context():
    prompt = build_prompt(
        "+app = FastAPI()", "initialize service",
        project_context="FILE: main.py\napp = FastAPI()",
    )
    assert "<project_context>" in prompt
    assert "FILE: main.py" in prompt


def test_endpoint_reports_unavailable_ollama():
    request = httpx.Request("POST", "http://localhost:11434/api/chat")
    with patch(
        "main.analyze_commit", side_effect=httpx.ConnectError("offline", request=request)
    ):
        response = TestClient(app).post(
            "/analyze-commit", json={"diff": "+ change", "commit_message": "test"}
        )
    assert response.status_code == 503


def test_repository_commit_to_analysis_pipeline():
    facts = {
        "hash": "a" * 40,
        "message": "feat: add health route",
        "changed_files": ["app.py"],
        "changed_file_entries": [{"status": "M", "path": "app.py", "old_path": None}],
        "stat_summary": "app.py | 1 +",
        "diff": "diff --git a/app.py b/app.py\n+++ b/app.py\n+app.get('/health')",
        "project_context": "FILE: app.py\napp.get('/health')",
    }
    analysis = {**VALID_RESPONSE, "change_type": "feature"}
    with patch("main.commit_evidence", return_value=facts), patch(
        "main.analyze_commit", return_value=analysis
    ) as analyze:
        response = TestClient(app).post(
            "/repository/analyze-commit", json={"path": ".", "commit": "HEAD"}
        )
    assert response.status_code == 200
    assert response.json()["repository_facts"]["hash"] == "a" * 40
    analyze.assert_called_once_with(
        facts["diff"], facts["message"],
        stat_summary=facts["stat_summary"], project_context=facts["project_context"],
    )
