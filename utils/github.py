"""
GitHub Manager for repository operations and PR creation
Handles GitHub API interactions, branch creation, and pull request management
"""

import os
import asyncio
from typing import Dict, List, Any, Optional
import requests
from git import Repo
import json

class GitHubManager:
    def __init__(self, owner: str, repo_name: str):
        self.owner = owner
        self.repo_name = repo_name
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.base_url = "https://api.github.com"
        
        if not self.github_token or self.github_token == 'your_personal_access_token_here':
            raise Exception("GitHub token not configured. Please set GITHUB_TOKEN in .env file")
        
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
    
    async def create_branch_and_commit(self, repo_path: str, branch_name: str, 
                                     commit_message: str, changes: List[Dict[str, Any]]) -> str:
        """
        Create a new branch, commit changes, and push to GitHub
        """
        try:
            repo = Repo(repo_path)
            
            # Ensure we're on the main/master branch
            main_branch = self._get_main_branch(repo)
            repo.git.checkout(main_branch)
            
            # Create and checkout new branch
            new_branch = repo.create_head(branch_name)
            repo.head.reference = new_branch
            repo.head.reset(index=True, working_tree=True)
            
            print(f"Created branch: {branch_name}")
            
            # Add all changes
            repo.git.add(A=True)
            
            # Check if there are changes to commit
            if not repo.is_dirty() and not repo.untracked_files:
                raise Exception("No changes to commit")
            
            # Commit changes
            commit = repo.index.commit(commit_message)
            print(f"Committed changes: {commit.hexsha[:8]}")
            
            # Push to GitHub
            origin = repo.remote('origin')
            
            # Set up authentication for push
            repo_url_with_token = self._get_authenticated_url(repo)
            origin.set_url(repo_url_with_token)
            
            # Push the new branch
            origin.push(refspec=f"{branch_name}:{branch_name}")
            print(f"Pushed branch {branch_name} to GitHub")
            
            return commit.hexsha
            
        except Exception as e:
            raise Exception(f"Failed to create branch and commit: {str(e)}")
    
    def _get_main_branch(self, repo: Repo) -> str:
        """Determine the main branch name (main or master)"""
        try:
            # Try to checkout main first
            try:
                repo.git.checkout('main')
                return 'main'
            except:
                repo.git.checkout('master')
                return 'master'
        except Exception:
            # If both fail, use the current branch
            return str(repo.active_branch)
    
    def _get_authenticated_url(self, repo: Repo) -> str:
        """Get repository URL with authentication token"""
        try:
            remote_url = repo.remote('origin').url
            
            # Handle different URL formats
            if remote_url.startswith('https://github.com/'):
                # Replace https://github.com/ with https://token@github.com/
                return remote_url.replace('https://github.com/', f'https://{self.github_token}@github.com/')
            elif remote_url.startswith('git@github.com:'):
                # Convert SSH to HTTPS with token
                repo_path = remote_url.replace('git@github.com:', '').replace('.git', '')
                return f'https://{self.github_token}@github.com/{repo_path}.git'
            else:
                # Assume it's already an HTTPS URL, add token
                return remote_url.replace('https://', f'https://{self.github_token}@')
                
        except Exception as e:
            raise Exception(f"Failed to create authenticated URL: {str(e)}")
    
    async def create_pull_request(self, branch: str, title: str, body: str, 
                                base_branch: str = "main") -> str:
        """
        Create a pull request on GitHub
        """
        try:
            # First try with 'main' as base, fallback to 'master'
            pr_url = await self._try_create_pr(branch, title, body, base_branch)
            if pr_url:
                return pr_url
            
            # If main failed, try master
            if base_branch == "main":
                pr_url = await self._try_create_pr(branch, title, body, "master")
                if pr_url:
                    return pr_url
            
            raise Exception("Failed to create PR with both 'main' and 'master' as base branch")
            
        except Exception as e:
            raise Exception(f"Failed to create pull request: {str(e)}")
    
    async def _try_create_pr(self, branch: str, title: str, body: str, base_branch: str) -> Optional[str]:
        """Try to create a PR with a specific base branch"""
        try:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo_name}/pulls"
            
            data = {
                "title": title,
                "body": body,
                "head": branch,
                "base": base_branch
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 201:
                pr_data = response.json()
                pr_url = pr_data['html_url']
                print(f"Pull request created successfully: {pr_url}")
                return pr_url
            elif response.status_code == 422:
                # Unprocessable entity - might be wrong base branch
                error_message = response.json().get('message', 'Unknown error')
                print(f"Failed to create PR with base '{base_branch}': {error_message}")
                return None
            else:
                response.raise_for_status()
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Request error when creating PR: {str(e)}")
            return None
    
    async def get_repository_info(self) -> Dict[str, Any]:
        """Get repository information from GitHub API"""
        try:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo_name}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            repo_data = response.json()
            
            return {
                "name": repo_data["name"],
                "full_name": repo_data["full_name"],
                "description": repo_data.get("description", ""),
                "language": repo_data.get("language", ""),
                "default_branch": repo_data["default_branch"],
                "clone_url": repo_data["clone_url"],
                "private": repo_data["private"],
                "fork": repo_data["fork"]
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get repository info: {str(e)}")
    
    async def check_permissions(self) -> Dict[str, bool]:
        """Check what permissions the token has on the repository"""
        try:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo_name}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            repo_data = response.json()
            permissions = repo_data.get("permissions", {})
            
            return {
                "admin": permissions.get("admin", False),
                "push": permissions.get("push", False),
                "pull": permissions.get("pull", False)
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to check permissions: {str(e)}")
    
    async def list_branches(self) -> List[str]:
        """List all branches in the repository"""
        try:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo_name}/branches"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            branches_data = response.json()
            return [branch["name"] for branch in branches_data]
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to list branches: {str(e)}")
    
    async def get_latest_commit(self, branch: str = None) -> Dict[str, Any]:
        """Get the latest commit from a branch"""
        try:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo_name}/commits"
            params = {}
            if branch:
                params["sha"] = branch
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            commits = response.json()
            if commits:
                latest = commits[0]
                return {
                    "sha": latest["sha"],
                    "message": latest["commit"]["message"],
                    "author": latest["commit"]["author"]["name"],
                    "date": latest["commit"]["author"]["date"]
                }
            else:
                return {}
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get latest commit: {str(e)}")
    
    async def create_issue_comment(self, issue_number: int, comment: str) -> str:
        """Create a comment on an issue or PR"""
        try:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo_name}/issues/{issue_number}/comments"
            
            data = {"body": comment}
            
            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            
            comment_data = response.json()
            return comment_data["html_url"]
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to create comment: {str(e)}")
    
    async def get_file_content(self, file_path: str, branch: str = None) -> str:
        """Get the content of a file from the repository"""
        try:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo_name}/contents/{file_path}"
            params = {}
            if branch:
                params["ref"] = branch
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            file_data = response.json()
            
            # Decode base64 content
            import base64
            content = base64.b64decode(file_data["content"]).decode('utf-8')
            return content
            
        except requests.exceptions.RequestException as e:
            if response.status_code == 404:
                raise Exception(f"File not found: {file_path}")
            else:
                raise Exception(f"Failed to get file content: {str(e)}")
    
    def validate_token(self) -> bool:
        """Validate that the GitHub token is working"""
        try:
            url = f"{self.base_url}/user"
            response = requests.get(url, headers=self.headers)
            return response.status_code == 200
            
        except:
            return False
    
    async def fork_repository(self) -> str:
        """Fork the repository to the authenticated user's account"""
        try:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo_name}/forks"
            
            response = requests.post(url, headers=self.headers)
            
            if response.status_code == 202:
                fork_data = response.json()
                return fork_data["clone_url"]
            else:
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fork repository: {str(e)}")
    
    async def delete_branch(self, branch_name: str) -> bool:
        """Delete a branch from the repository"""
        try:
            url = f"{self.base_url}/repos/{self.owner}/{self.repo_name}/git/refs/heads/{branch_name}"
            
            response = requests.delete(url, headers=self.headers)
            
            return response.status_code == 204
            
        except requests.exceptions.RequestException as e:
            print(f"Warning: Failed to delete branch {branch_name}: {str(e)}")
            return False
