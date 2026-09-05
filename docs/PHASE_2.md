# Phase 2 — Git and Repository Intelligence

Phase 2 establishes repository facts deterministically with Git and filesystem
parsers. The LLM is used only after these facts have been collected.

## Implemented operations

- Repository root discovery from the root or any subdirectory
- Current branch and detached-HEAD reporting
- Structured staged, unstaged, renamed, and untracked status
- Recent commit metadata
- Commit changed-file statuses and rename metadata
- Relevant commit diff with generated lockfiles excluded
- Changed-file content at the selected commit
- npm, requirements.txt, and pyproject.toml dependency parsing
- Bounded project file tree
- Combined commit-to-Phase-1 analysis endpoint

## API endpoints

All repository endpoints accept a local `path` in their JSON body.

- `POST /repository/info`
- `POST /repository/branch`
- `POST /repository/status`
- `POST /repository/commits`
- `POST /repository/commit`
- `POST /repository/changed-files`
- `POST /repository/diff`
- `POST /repository/dependencies`
- `POST /repository/structure`
- `POST /repository/analyze-commit`

## Manual verification

From `ai-service`:

```powershell
python test_git_manual.py "D:\path\to\repository" HEAD
```

To run the full commit-to-LLM pipeline:

```powershell
python test_manual.py <commit-hash>
```
