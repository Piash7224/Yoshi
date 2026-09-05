# Yoshi Architecture Specifications & Communication Contract

This document captures the communication architecture, operational flow, and payload schemas defining data translation between the Node/Express core and the Python FastAPI/Ollama analysis engine, matching the Phase 1 specification metrics.

---

## 1. System Topology Overview

```text
[ React Frontend ] 
       │  ▲
       │  │ (HTTP / JSON)
       ▼  │
[ Node.js / Express Backend ] ◄───► [ MongoDB Atlas (Structured Application Memory) ]
       │  ▲
       │  │ (Internal HTTP / REST Contract)
       ▼  │
[ Python FastAPI Engine ] ◄───────► [ Local Ollama Service (llama3.2:3b) ]
```

The model can be changed with `OLLAMA_MODEL`. Calls time out after 120 seconds
by default; override this with `OLLAMA_TIMEOUT_SECONDS` when needed.

---

## 2. Core Architectural Principle
> **Deterministic systems establish the facts; AI interprets those facts.**

The Node/Express and local Git integrations deterministically extract exact diffs, commit metadata, and changed file paths. The Python AI service acts strictly as an interpretation engine to synthesize intent, change impact, and cross-component updates.

---

## 3. Express ↔ Python API Contract

### Endpoint: `POST /analyze-commit`
Triggered by the Express gateway when processing a developer workspace commit submission payload.

### A. Inbound Request Schema (Express ──> Python)
* **URL Target:** `http://localhost:8000/analyze-commit`
* **Content-Type:** `application/json`

```json
{
  "diff": "String containing the standard git diff content showing line removals and additions.",
  "commit_message": "The original developer-provided commit string description.",
  "stat_summary": "Optional deterministic git --stat output."
}
```

---

### B. Outbound Response Schema (Python ──> Express)
* **Status Code:** `200 OK`
* **Content-Type:** `application/json`

Matches the exact Phase 1 structural output contract:
```json
{
  "summary": "High-level summary text synthesizing the intent and impact of the changes.",
  "changed_components": [
    "src/model.py",
    "src/train.py"
  ],
  "change_type": "feature | bugfix | refactor | docs | test | chore",
  "risk_level": "low | medium | high",
  "reasoning": "Brief evidence-based justification for the classification and risk."
}
```

---

## 4. Storage Allocations (Phase 3+ Target)

1. **MongoDB Application Memory:** 
   * Tracks structured layout definitions, including metadata fields for `Project`, `Repository`, `Commit`, and `ProjectEvent`.
2. **Vector Store Semantic Memory:** 
   * Unstructured embeddings mapping historical architecture reasoning, codebase decisions, and experimental summaries.
