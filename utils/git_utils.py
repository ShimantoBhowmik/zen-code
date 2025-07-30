"""
Git utilities for repository operations
"""

import os
import subprocess
from typing import List, Dict, Any
from git import Repo
import git

def get_repo_info(repo_path: str) -> Dict[str, Any]:
    """Get basic repository information"""
    try:
        repo = Repo(repo_path)
        
        info = {
            "is_repo": True,
            "active_branch": str(repo.active_branch),
            "is_dirty": repo.is_dirty(),
            "untracked_files": repo.untracked_files,
            "commit_count": len(list(repo.iter_commits())),
            "remotes": [remote.name for remote in repo.remotes]
        }
        
        # Get remote URL if available
        if repo.remotes:
            info["remote_url"] = repo.remotes[0].url
        
        return info
        
    except (git.exc.InvalidGitRepositoryError, git.exc.GitCommandError):
        return {"is_repo": False, "error": "Not a valid git repository"}

def create_gitignore(repo_path: str, template: str = "python"):
    """Create a .gitignore file with common patterns"""
    
    templates = {
        "python": [
            "# Python",
            "__pycache__/",
            "*.py[cod]",
            "*$py.class",
            "*.so",
            ".Python",
            "env/",
            "venv/",
            ".env",
            ".venv",
            "pip-log.txt",
            "pip-delete-this-directory.txt",
            ".pytest_cache/",
            ".coverage",
            "htmlcov/",
            "*.egg-info/",
            "dist/",
            "build/"
        ],
        "node": [
            "# Node.js",
            "node_modules/",
            "npm-debug.log*",
            "yarn-debug.log*",
            "yarn-error.log*",
            ".npm",
            ".node_repl_history",
            "*.tgz",
            "*.tar.gz",
            ".env",
            ".env.local",
            ".env.development.local",
            ".env.test.local",
            ".env.production.local",
            "dist/",
            "tmp/",
            ".cache/"
        ],
        "general": [
            "# General",
            ".DS_Store",
            "Thumbs.db",
            "*.log",
            "*.tmp",
            "*.temp",
            ".env",
            ".env.local",
            "*.backup",
            "*.swp",
            "*.swo",
            "*~"
        ]
    }
    
    gitignore_path = os.path.join(repo_path, ".gitignore")
    
    # Check if .gitignore already exists
    if os.path.exists(gitignore_path):
        return f".gitignore already exists at {gitignore_path}"
    
    # Get patterns for the template
    patterns = templates.get(template, templates["general"])
    
    # Write .gitignore file
    with open(gitignore_path, 'w') as f:
        f.write("\\n".join(patterns))
        f.write("\\n")
    
    return f"Created .gitignore with {template} template"

def get_changed_files(repo_path: str) -> Dict[str, List[str]]:
    """Get lists of changed files by category"""
    try:
        repo = Repo(repo_path)
        
        return {
            "modified": [item.a_path for item in repo.index.diff(None)],
            "staged": [item.a_path for item in repo.index.diff("HEAD")],
            "untracked": repo.untracked_files,
            "deleted": [item.a_path for item in repo.index.diff(None) if item.deleted_file]
        }
        
    except Exception as e:
        return {"error": str(e)}

def validate_repo_url(url: str) -> Dict[str, Any]:
    """Validate and parse a GitHub repository URL"""
    import re
    
    # Common GitHub URL patterns
    patterns = [
        r"https://github\.com/([^/]+)/([^/]+)/?(?:\.git)?$",
        r"git@github\.com:([^/]+)/([^/]+)\.git$",
        r"github\.com/([^/]+)/([^/]+)/?$"
    ]
    
    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            owner, repo = match.groups()
            return {
                "valid": True,
                "owner": owner,
                "repo": repo.replace('.git', ''),
                "https_url": f"https://github.com/{owner}/{repo.replace('.git', '')}.git",
                "ssh_url": f"git@github.com:{owner}/{repo.replace('.git', '')}.git"
            }
    
    return {
        "valid": False,
        "error": "Invalid GitHub repository URL format"
    }
