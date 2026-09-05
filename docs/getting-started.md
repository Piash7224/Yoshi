# Getting Started

## Prerequisites

- Python 3.11+
- Node.js 20+
- MongoDB running locally
- Ollama running with `llama3.2:3b`

## Install

```powershell
cd "D:\courses\AI AGENT BUILDER\Yoshi"
python -m pip install -r ai-service\requirements-phase1.txt
npm --prefix backend install
npm --prefix frontend install
Copy-Item backend\.env.example backend\.env
```

Adjust `backend/.env` if MongoDB is not at
`mongodb://127.0.0.1:27017/yoshi`.

## Run

Open three PowerShell terminals.

Terminal 1:

```powershell
cd "D:\courses\AI AGENT BUILDER\Yoshi\ai-service"
python -m uvicorn main:app --reload
```

Terminal 2:

```powershell
cd "D:\courses\AI AGENT BUILDER\Yoshi\backend"
npm run dev
```

Terminal 3:

```powershell
cd "D:\courses\AI AGENT BUILDER\Yoshi\frontend"
npm run dev
```

Open `http://127.0.0.1:5173`, connect a local Git repository, then use:

1. **Scan & index** to build its profile, audit, commit list, and memory.
2. **Analyze HEAD** to create a structured timeline event.
3. **Project knowledge** to ask grounded questions about indexed files.

Re-run **Scan & index** after files change so local memory stays current.

## Verify

```powershell
cd ai-service
python -m pytest -q
cd ..\backend
npm test
cd ..\frontend
npm run build
npm run lint
```

## Phase Coverage

| Phase | Testable baseline |
|---|---|
| 0–1 | Local services and schema-validated Ollama analysis |
| 2 | Deterministic Git inspection and commit evidence |
| 3 | Express/MongoDB projects, events, and dashboard |
| 4 | Project files, languages, manifests, and profile |
| 5 | Persistent local index, retrieval, grounded Q&A |
| 6 | Documentation inventory and missing-doc suggestions |
| 7 | Readiness score, repository checks, secret-pattern scan |
| 8 | Read-only agent plan requiring approval; no mutation yet |
| 9 | Model and timeout configuration for local experiments |
| 10 | Automated tests, bounded inputs, timeouts, and error handling |

## Important Boundaries

- Git determines facts; the LLM interprets supplied evidence.
- The memory index is local and repository-specific.
- Readiness secret checks are a first-pass heuristic, not a security guarantee.
- Agent plans never edit files. Mutation must be added later with explicit
  per-action approval, path restrictions, backups, and validation.
