"""
Sandbox Runner for secure code execution
Handles repository cloning, change application, and cleanup
"""

import os
import shutil
import asyncio
import tempfile
from typing import Dict, List, Any, Optional
from pathlib import Path
import git
from git import Repo
import aiofiles

class SandboxRunner:
    def __init__(self):
        self.sandbox_dir = os.getenv('SANDBOX_DIR', '/tmp/backspace-sandbox')
        self.max_repo_size_mb = int(os.getenv('MAX_REPO_SIZE_MB', '100'))
        self.current_repo_path = None
        
        # Ensure sandbox directory exists
        Path(self.sandbox_dir).mkdir(parents=True, exist_ok=True)
    
    async def clone_repository(self, repo_url: str) -> str:
        """
        Clone a repository into the sandbox environment
        """
        try:
            # Extract repo name from URL
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            
            # Create unique directory for this clone
            import time
            timestamp = int(time.time())
            repo_path = os.path.join(self.sandbox_dir, f"{repo_name}-{timestamp}")
            
            # Clone the repository
            print(f"Cloning {repo_url} to {repo_path}")
            
            # Use asyncio to run git clone in a thread
            await asyncio.get_event_loop().run_in_executor(
                None, 
                self._clone_repo_sync, 
                repo_url, 
                repo_path
            )
            
            # Validate repository size
            await self._validate_repo_size(repo_path)
            
            self.current_repo_path = repo_path
            return repo_path
            
        except Exception as e:
            raise Exception(f"Failed to clone repository: {str(e)}")
    
    def _clone_repo_sync(self, repo_url: str, repo_path: str):
        """Synchronous git clone operation"""
        try:
            # Clone with depth=1 for faster cloning
            Repo.clone_from(
                repo_url, 
                repo_path, 
                depth=1,
                single_branch=True
            )
        except git.exc.GitCommandError as e:
            raise Exception(f"Git clone failed: {str(e)}")
    
    async def _validate_repo_size(self, repo_path: str):
        """Validate that the repository size is within limits"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(repo_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
            
            size_mb = total_size / (1024 * 1024)
            
            if size_mb > self.max_repo_size_mb:
                raise Exception(f"Repository size ({size_mb:.1f}MB) exceeds limit ({self.max_repo_size_mb}MB)")
            
            print(f"Repository size: {size_mb:.1f}MB")
            
        except Exception as e:
            raise Exception(f"Failed to validate repository size: {str(e)}")
    
    async def apply_changes(self, repo_path: str, changes: List[Dict[str, Any]]):
        """
        Apply the generated code changes to the repository
        """
        try:
            applied_changes = []
            
            for change in changes:
                action = change.get('action')
                file_path = change.get('file_path')
                content = change.get('content', '')
                
                if not file_path:
                    continue
                
                absolute_path = os.path.join(repo_path, file_path)
                
                if action == 'create':
                    await self._create_file(absolute_path, content)
                    applied_changes.append(f"Created: {file_path}")
                    
                elif action == 'modify':
                    await self._modify_file(absolute_path, content)
                    applied_changes.append(f"Modified: {file_path}")
                    
                elif action == 'delete':
                    await self._delete_file(absolute_path)
                    applied_changes.append(f"Deleted: {file_path}")
                
            print(f"Applied {len(applied_changes)} changes:")
            for change in applied_changes:
                print(f"  - {change}")
                
        except Exception as e:
            raise Exception(f"Failed to apply changes: {str(e)}")
    
    async def _create_file(self, file_path: str, content: str):
        """Create a new file with the given content"""
        try:
            # Ensure parent directory exists
            parent_dir = os.path.dirname(file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            # Write the file
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
                
        except Exception as e:
            raise Exception(f"Failed to create file {file_path}: {str(e)}")
    
    async def _modify_file(self, file_path: str, content: str):
        """Modify an existing file or create it if it doesn't exist"""
        try:
            # Ensure parent directory exists
            parent_dir = os.path.dirname(file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            # Backup original file if it exists
            if os.path.exists(file_path):
                backup_path = f"{file_path}.backup"
                shutil.copy2(file_path, backup_path)
            
            # Write the new content
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
                
        except Exception as e:
            raise Exception(f"Failed to modify file {file_path}: {str(e)}")
    
    async def _delete_file(self, file_path: str):
        """Delete a file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            else:
                print(f"Warning: File {file_path} does not exist, skipping deletion")
                
        except Exception as e:
            raise Exception(f"Failed to delete file {file_path}: {str(e)}")
    
    async def get_git_diff(self, repo_path: str) -> str:
        """Get git diff of current changes"""
        try:
            repo = Repo(repo_path)
            
            # Get unstaged changes
            unstaged_diff = repo.git.diff()
            
            # Get staged changes
            staged_diff = repo.git.diff('--cached')
            
            # Combine diffs
            full_diff = ""
            if unstaged_diff:
                full_diff += "Unstaged changes:\\n" + unstaged_diff + "\\n\\n"
            if staged_diff:
                full_diff += "Staged changes:\\n" + staged_diff + "\\n"
            
            return full_diff if full_diff else "No changes detected"
            
        except Exception as e:
            return f"Error getting diff: {str(e)}"
    
    async def validate_changes(self, repo_path: str) -> Dict[str, Any]:
        """
        Validate that the changes don't break basic functionality
        This is a basic validation - can be extended with linting, testing, etc.
        """
        validation_results = {
            "valid": True,
            "issues": [],
            "warnings": []
        }
        
        try:
            # Check for syntax errors in Python files
            await self._validate_python_files(repo_path, validation_results)
            
            # Check for syntax errors in JavaScript/TypeScript files
            await self._validate_js_files(repo_path, validation_results)
            
            # Check for broken imports (basic check)
            await self._validate_imports(repo_path, validation_results)
            
        except Exception as e:
            validation_results["valid"] = False
            validation_results["issues"].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    async def _validate_python_files(self, repo_path: str, results: Dict[str, Any]):
        """Basic Python syntax validation"""
        import ast
        
        for root, dirs, files in os.walk(repo_path):
            # Skip .git and other hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    try:
                        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                            content = await f.read()
                        
                        # Try to parse the Python file
                        ast.parse(content)
                        
                    except SyntaxError as e:
                        results["valid"] = False
                        results["issues"].append(f"Python syntax error in {file}: {str(e)}")
                    except Exception as e:
                        results["warnings"].append(f"Could not validate {file}: {str(e)}")
    
    async def _validate_js_files(self, repo_path: str, results: Dict[str, Any]):
        """Basic JavaScript/TypeScript validation (placeholder)"""
        # This would require a JavaScript parser like esprima
        # For now, just check for basic syntax issues
        
        js_extensions = ['.js', '.jsx', '.ts', '.tsx']
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if any(file.endswith(ext) for ext in js_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                            content = await f.read()
                        
                        # Basic checks for common syntax issues
                        if content.count('{') != content.count('}'):
                            results["warnings"].append(f"Possible brace mismatch in {file}")
                        
                        if content.count('(') != content.count(')'):
                            results["warnings"].append(f"Possible parenthesis mismatch in {file}")
                            
                    except Exception as e:
                        results["warnings"].append(f"Could not validate {file}: {str(e)}")
    
    async def _validate_imports(self, repo_path: str, results: Dict[str, Any]):
        """Basic import validation"""
        # This is a simplified check - could be enhanced with proper AST analysis
        pass
    
    async def cleanup(self):
        """Clean up the sandbox environment"""
        try:
            if self.current_repo_path and os.path.exists(self.current_repo_path):
                shutil.rmtree(self.current_repo_path)
                print(f"Cleaned up sandbox: {self.current_repo_path}")
                self.current_repo_path = None
                
        except Exception as e:
            print(f"Warning: Failed to cleanup sandbox: {str(e)}")
    
    def get_repo_info(self, repo_path: str) -> Dict[str, Any]:
        """Get basic information about the repository"""
        try:
            repo = Repo(repo_path)
            
            return {
                "active_branch": repo.active_branch.name,
                "commit_count": len(list(repo.iter_commits())),
                "remote_url": repo.remote().url if repo.remotes else None,
                "is_dirty": repo.is_dirty(),
                "untracked_files": repo.untracked_files
            }
            
        except Exception as e:
            return {"error": f"Failed to get repo info: {str(e)}"}
    
    async def create_branch(self, repo_path: str, branch_name: str) -> str:
        """Create and checkout a new branch"""
        try:
            repo = Repo(repo_path)
            
            # Create new branch
            new_branch = repo.create_head(branch_name)
            
            # Checkout the new branch
            repo.head.reference = new_branch
            repo.head.reset(index=True, working_tree=True)
            
            print(f"Created and checked out branch: {branch_name}")
            return branch_name
            
        except Exception as e:
            raise Exception(f"Failed to create branch: {str(e)}")
    
    async def commit_changes(self, repo_path: str, commit_message: str) -> str:
        """Add and commit all changes"""
        try:
            repo = Repo(repo_path)
            
            # Add all changes
            repo.git.add(A=True)
            
            # Commit changes
            commit = repo.index.commit(commit_message)
            
            print(f"Committed changes: {commit.hexsha[:8]}")
            return commit.hexsha
            
        except Exception as e:
            raise Exception(f"Failed to commit changes: {str(e)}")
