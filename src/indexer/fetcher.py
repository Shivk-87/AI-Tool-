import os
import subprocess
from pathlib import Path

STAGING_DIR = Path("/tmp/codebase_steward_staging")

def clone_repo(repo_url: str, dest_subdir: str) -> str:
    """Clone a git repo into the staging area and return the local path.

    repo_url: HTTPS URL of the repository.
    dest_subdir: subdirectory name under staging for this repo.
    """
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    dest = STAGING_DIR / dest_subdir
    if dest.exists():
        # If exists, remove and reclone for idempotency in tests
        subprocess.run(["rm", "-rf", str(dest)], check=True)
    dest_parent = dest.parent
    dest_parent.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", repo_url, str(dest)]
    try:
        subprocess.run(cmd, check=True)
        return str(dest)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to clone {repo_url}: {e}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("Usage: python fetcher.py <repo_url> <dest_subdir>")
        sys.exit(1)
    print(clone_repo(sys.argv[1], sys.argv[2]))
