from fastapi import FastAPI, HTTPException

import ollama
import httpx

from schemas import CommitAnalysisRequest, CommitAnalysis, CommitRequest, HistoryRequest, QueryRequest, RepositoryRequest
from llm_service import analyze_commit, answer_project_question
from project_engine import (
    ProjectError, agent_plan, build_memory, commit_evidence, documentation_status,
    get_changed_files, get_commit_diff, get_current_branch, get_dependencies,
    get_git_status, get_project_structure, project_profile, readiness_audit,
    recent_commits, repository_info, retrieve,
)

app = FastAPI(title="Yoshi AI Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze-commit", response_model=CommitAnalysis)
def analyze_commit_endpoint(request: CommitAnalysisRequest):
    if not request.diff.strip():
        raise HTTPException(status_code=422, detail="diff must not be blank")
    try:
        return analyze_commit(
            request.diff,
            request.commit_message,
            stat_summary=request.stat_summary,
            project_context=request.project_context,
        )
    except ollama.ResponseError as exc:
        raise HTTPException(
            status_code=502, detail=f"Ollama rejected the request: {exc.error}"
        ) from exc
    except (httpx.RequestError, ConnectionError, OSError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Ollama is unavailable. Start Ollama and verify OLLAMA_MODEL.",
        ) from exc


@app.post("/repository/info")
def repository_info_endpoint(request: RepositoryRequest):
    return _project_call(repository_info, request.path)


@app.post("/repository/commits")
def commits_endpoint(request: HistoryRequest):
    return _project_call(recent_commits, request.path, request.limit)


@app.post("/repository/branch")
def branch_endpoint(request: RepositoryRequest):
    return {"branch": _project_call(get_current_branch, request.path)}


@app.post("/repository/status")
def status_endpoint(request: RepositoryRequest):
    return _project_call(get_git_status, request.path)


@app.post("/repository/commit")
def commit_endpoint(request: CommitRequest):
    return _project_call(commit_evidence, request.path, request.commit)


@app.post("/repository/analyze-commit")
def repository_analyze_commit_endpoint(request: CommitRequest):
    evidence = _project_call(commit_evidence, request.path, request.commit)
    try:
        analysis = analyze_commit(
            evidence["diff"], evidence["message"],
            stat_summary=evidence["stat_summary"],
            project_context=evidence["project_context"],
        )
        return {"repository_facts": evidence, "analysis": analysis}
    except ollama.ResponseError as exc:
        raise HTTPException(status_code=502, detail=f"Ollama rejected the request: {exc.error}") from exc
    except (httpx.RequestError, ConnectionError, OSError) as exc:
        raise HTTPException(status_code=503, detail="Ollama is unavailable.") from exc


@app.post("/repository/changed-files")
def changed_files_endpoint(request: CommitRequest):
    return _project_call(get_changed_files, request.path, request.commit)


@app.post("/repository/diff")
def diff_endpoint(request: CommitRequest):
    return {"diff": _project_call(get_commit_diff, request.path, request.commit)}


@app.post("/repository/dependencies")
def dependencies_endpoint(request: RepositoryRequest):
    return _project_call(get_dependencies, request.path)


@app.post("/repository/structure")
def structure_endpoint(request: RepositoryRequest):
    return _project_call(get_project_structure, request.path)


@app.post("/repository/profile")
def profile_endpoint(request: RepositoryRequest):
    return _project_call(project_profile, request.path)


@app.post("/repository/readiness")
def readiness_endpoint(request: RepositoryRequest):
    return _project_call(readiness_audit, request.path)


@app.post("/repository/documentation")
def documentation_endpoint(request: RepositoryRequest):
    return _project_call(documentation_status, request.path)


@app.post("/memory/index")
def memory_index_endpoint(request: RepositoryRequest):
    return _project_call(build_memory, request.path)


@app.post("/memory/retrieve")
def memory_retrieve_endpoint(request: QueryRequest):
    return _project_call(retrieve, request.path, request.question, request.limit)


@app.post("/memory/query")
def memory_query_endpoint(request: QueryRequest):
    sources = _project_call(retrieve, request.path, request.question, request.limit)
    return answer_project_question(request.question, sources)


@app.post("/agent/plan")
def agent_plan_endpoint(request: QueryRequest):
    return _project_call(agent_plan, request.path, request.question)


def _project_call(function, *args):
    try:
        return function(*args)
    except ProjectError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
