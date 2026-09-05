"""Print Phase 2 deterministic repository facts without requiring Ollama."""

import json
import sys

from project_engine import (
    get_changed_files,
    get_current_branch,
    get_dependencies,
    get_git_status,
    get_project_structure,
    recent_commits,
    repository_info,
)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    commit = sys.argv[2] if len(sys.argv) > 2 else "HEAD"
    structure = get_project_structure(path)
    output = {
        "repository": repository_info(path),
        "branch": get_current_branch(path),
        "status": get_git_status(path),
        "recent_commits": recent_commits(path, 5),
        "selected_commit": commit,
        "changed_files": get_changed_files(path, commit),
        "dependencies": get_dependencies(path),
        "structure": {
            "file_count": structure["file_count"],
            "truncated": structure["truncated"],
            "directories": structure["directories"],
            "root_files": structure["root_files"],
        },
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
