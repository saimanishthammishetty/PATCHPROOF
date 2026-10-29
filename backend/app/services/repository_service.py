import os
import shutil
import subprocess
import hashlib
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from app.core.config import TEMP_DIR, FIXTURES_DIR
from app.core.security import validate_repository_url

class RepositoryService:
    @staticmethod
    def setup_repository(repo_url: str, branch: Optional[str] = None) -> Tuple[Path, str, str, str]:
        """
        Retrieves or locates the repository.
        Returns: (repo_path, repo_name, commit_sha, default_branch)
        """
        # Check if URL references a local test fixture
        if repo_url.startswith("fixture://"):
            fixture_name = repo_url.replace("fixture://", "").strip()
            fixture_path = FIXTURES_DIR / fixture_name
            if not fixture_path.exists():
                raise FileNotFoundError(f"Fixture '{fixture_name}' not found at {fixture_path}")
            
            commit_sha = hashlib.sha256(fixture_name.encode()).hexdigest()[:12]
            return fixture_path, fixture_name, commit_sha, "main"
        
        # Validate GitHub URL
        valid, msg = validate_repository_url(repo_url)
        if not valid:
            raise ValueError(msg)
        
        # Compute safe unique folder name
        url_hash = hashlib.sha256(f"{repo_url}::{branch}".encode()).hexdigest()[:12]
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        target_dir = TEMP_DIR / f"{repo_name}_{url_hash}"
        
        # Clean existing folder if needed
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)
            
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Perform shallow clone
        clone_cmd = ["git", "clone", "--depth", "1"]
        if branch:
            clone_cmd.extend(["--branch", branch])
        clone_cmd.extend([repo_url, str(target_dir)])
        
        try:
            res = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                timeout=45,
                check=False
            )
            if res.returncode != 0:
                # If branch failed or shallow clone had issues, raise meaningful error
                err_msg = res.stderr.strip() or "Git clone failed"
                raise RuntimeError(f"Failed to clone repository: {err_msg}")
        except subprocess.TimeoutExpired:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise TimeoutError("Repository cloning timed out (limit: 45s). Repository may be too large.")
        
        # Get head commit SHA
        sha_res = subprocess.run(
            ["git", "-C", str(target_dir), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )
        commit_sha = sha_res.stdout.strip() if sha_res.returncode == 0 else "unknown_sha"
        
        return target_dir, repo_name, commit_sha, branch or "main"

    @staticmethod
    def detect_ecosystems(repo_path: Path) -> Dict[str, Any]:
        """
        Detects available manifests and ecosystems in the repository.
        """
        manifests = {
            "pypi": [],
            "npm": [],
            "golang": [],
            "maven": []
        }
        
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden and vendor folders
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", ".venv", "vendor")]
            
            rel_root = Path(root).relative_to(repo_path)
            
            for file in files:
                file_lower = file.lower()
                rel_file = str(rel_root / file) if str(rel_root) != "." else file
                
                # Python
                if file_lower in ("requirements.txt", "pyproject.toml", "poetry.lock", "pipfile", "setup.py"):
                    manifests["pypi"].append(rel_file)
                # JavaScript / TypeScript
                elif file_lower in ("package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"):
                    manifests["npm"].append(rel_file)
                # Go
                elif file_lower in ("go.mod", "go.sum"):
                    manifests["golang"].append(rel_file)
                # Java
                elif file_lower in ("pom.xml", "build.gradle", "build.gradle.kts"):
                    manifests["maven"].append(rel_file)
                    
        return manifests

    @staticmethod
    def cleanup(repo_path: Path) -> None:
        """Safely cleans up temporary clone directory."""
        if repo_path and repo_path.exists() and str(TEMP_DIR) in str(repo_path):
            shutil.rmtree(repo_path, ignore_errors=True)
