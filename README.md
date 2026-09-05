# Yoshi — Local AI Project Companion

Yoshi connects to a local Git repository, creates deterministic project facts,
uses Ollama for grounded interpretation, stores projects and timeline events in
MongoDB, and exposes everything through a React dashboard.

## Implemented MVP

- Local structured commit analysis with schema validation and retry
- Git metadata, history, diffs, changed files, and project profiles
- MongoDB projects and analyzed-commit timeline events
- Local project-memory indexing, retrieval, and grounded project Q&A
- Documentation status and GitHub-readiness audits
- Secret-pattern checks and approval-gated agent plans
- Configurable local model and inference timeout
- FastAPI, Express, and frontend validation suites

The agent currently creates read-only plans. File-changing execution remains
intentionally disabled until an explicit approval workflow is implemented.

See [docs/getting-started.md](docs/getting-started.md) for setup and testing.

## Structure

- `frontend/` — React + Vite dashboard
- `backend/` — Express orchestration and MongoDB persistence
- `ai-service/` — FastAPI, Ollama, Git intelligence, memory, and audits
- `docs/` — architecture and operating documentation
