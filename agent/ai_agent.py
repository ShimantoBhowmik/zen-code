"""
AI Agent for code analysis and modification
Handles interaction with local LLMs (Ollama, GPT4All) or OpenAI API
"""

import os
import json
import aiofiles
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
import requests
from openai import OpenAI

class AIAgent:
    def __init__(self, model: str = "codellama"):
        self.model = model
        self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        # Initialize OpenAI client if API key is provided
        self.openai_client = None
        if self.openai_api_key and self.openai_api_key != 'your_openai_api_key_here':
            self.openai_client = OpenAI(api_key=self.openai_api_key)
    
    async def analyze_codebase(self, repo_path: str, prompt: str) -> Dict[str, Any]:
        """
        Analyze the codebase to understand structure and context
        """
        try:
            # Get repository structure
            structure = await self._get_repo_structure(repo_path)
            
            # Read key files (README, package.json, requirements.txt, etc.)
            key_files = await self._read_key_files(repo_path)
            
            # Analyze with AI
            analysis_prompt = self._build_analysis_prompt(structure, key_files, prompt)
            
            analysis_result = await self._query_ai(
                prompt=analysis_prompt,
                system_message="You are a senior software engineer analyzing a codebase to understand its structure and plan modifications."
            )
            
            return {
                "summary": analysis_result,
                "structure": structure,
                "key_files": key_files,
                "analysis_text": analysis_result
            }
            
        except Exception as e:
            raise Exception(f"Failed to analyze codebase: {str(e)}")
    
    async def generate_changes(self, repo_path: str, prompt: str, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate specific code changes based on the prompt and analysis
        """
        try:
            # Build the code generation prompt
            generation_prompt = self._build_generation_prompt(prompt, analysis)
            
            # Get AI response
            changes_result = await self._query_ai(
                prompt=generation_prompt,
                system_message="You are an expert software engineer. Generate specific, actionable code changes in JSON format."
            )
            
            # Parse the changes (expecting JSON format)
            changes = self._parse_changes_response(changes_result)
            
            # Validate and enhance changes
            validated_changes = await self._validate_changes(repo_path, changes)
            
            return validated_changes
            
        except Exception as e:
            raise Exception(f"Failed to generate changes: {str(e)}")
    
    async def _get_repo_structure(self, repo_path: str) -> Dict[str, Any]:
        """Get the repository file structure"""
        structure = {"files": [], "directories": []}
        
        try:
            repo_pathlib = Path(repo_path)
            
            # Walk through the repository
            for item in repo_pathlib.rglob("*"):
                # Skip hidden files and common build/cache directories
                if any(part.startswith('.') for part in item.parts):
                    continue
                if any(skip_dir in str(item) for skip_dir in ['node_modules', '__pycache__', '.git', 'venv', '.env']):
                    continue
                    
                relative_path = str(item.relative_to(repo_pathlib))
                
                if item.is_file():
                    structure["files"].append({
                        "path": relative_path,
                        "size": item.stat().st_size,
                        "extension": item.suffix
                    })
                elif item.is_dir():
                    structure["directories"].append(relative_path)
            
            return structure
            
        except Exception as e:
            raise Exception(f"Failed to analyze repository structure: {str(e)}")
    
    async def _read_key_files(self, repo_path: str) -> Dict[str, str]:
        """Read important files that provide context about the project"""
        key_files = {}
        key_file_patterns = [
            'README.md', 'README.txt', 'readme.md',
            'package.json', 'requirements.txt', 'pyproject.toml',
            'Dockerfile', 'docker-compose.yml',
            'tsconfig.json', 'babel.config.js',
            '.env.example', 'config.py', 'settings.py'
        ]
        
        repo_pathlib = Path(repo_path)
        
        for pattern in key_file_patterns:
            file_path = repo_pathlib / pattern
            if file_path.exists() and file_path.is_file():
                try:
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        # Limit content size to avoid token limits
                        if len(content) > 5000:
                            content = content[:5000] + "\\n... (truncated)"
                        key_files[pattern] = content
                except Exception as e:
                    key_files[pattern] = f"Error reading file: {str(e)}"
        
        return key_files
    
    def _build_analysis_prompt(self, structure: Dict[str, Any], key_files: Dict[str, str], user_prompt: str) -> str:
        """Build the prompt for codebase analysis"""
        
        files_list = "\\n".join([f"- {f['path']} ({f.get('extension', 'no ext')})" for f in structure['files'][:50]])
        dirs_list = "\\n".join([f"- {d}/" for d in structure['directories'][:20]])
        
        key_files_content = ""
        for filename, content in key_files.items():
            key_files_content += f"\\n### {filename}\\n```\\n{content}\\n```\\n"
        
        return f"""
I need you to analyze this codebase and understand its structure to help implement the following change:

**User Request:** {user_prompt}

**Repository Structure:**

**Files:**
{files_list}

**Directories:**
{dirs_list}

**Key Files Content:**
{key_files_content}

Please provide:
1. What type of project this is (web app, library, CLI tool, etc.)
2. What technologies/frameworks are being used
3. The main entry points and important modules
4. How the requested change should be implemented
5. What files will likely need to be modified
6. Any potential challenges or considerations

Provide a clear, concise analysis that will help guide the code generation process.
"""
    
    def _build_generation_prompt(self, user_prompt: str, analysis: Dict[str, Any]) -> str:
        """Build the prompt for code generation"""
        
        return f"""
Based on the following codebase analysis, generate specific code changes to implement the user's request.

**User Request:** {user_prompt}

**Codebase Analysis:**
{analysis.get('analysis_text', 'No analysis available')}

**Repository Structure:**
Files: {len(analysis.get('structure', {}).get('files', []))} files
Key files: {', '.join(analysis.get('key_files', {}).keys())}

Please generate the changes in the following JSON format:

```json
{{
  "changes": [
    {{
      "action": "create|modify|delete",
      "file_path": "relative/path/to/file",
      "content": "full file content for create/modify, empty for delete",
      "description": "what this change does"
    }}
  ],
  "summary": "overall description of changes"
}}
```

Requirements:
- Provide complete file content for new/modified files
- Use proper indentation and formatting
- Follow the existing code style and patterns
- Include appropriate error handling
- Add comments where helpful
- Ensure the changes work together as a cohesive solution

Generate practical, working code that implements the requested feature.
"""
    
    def _parse_changes_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the AI response to extract code changes"""
        try:
            # Try to find JSON in the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[start_idx:end_idx]
            parsed = json.loads(json_str)
            
            return parsed.get('changes', [])
            
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: try to extract changes manually
            print(f"Warning: Could not parse JSON response: {e}")
            print(f"Response was: {response[:500]}...")
            
            # Return a simple structure for manual parsing
            return [{
                "action": "modify",
                "file_path": "PARSE_ERROR.txt",
                "content": response,
                "description": "Failed to parse AI response - manual review needed"
            }]
    
    async def _validate_changes(self, repo_path: str, changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and enhance the generated changes"""
        validated_changes = []
        
        for change in changes:
            # Ensure required fields
            if 'action' not in change or 'file_path' not in change:
                continue
            
            # Normalize file path
            file_path = change['file_path'].lstrip('./')
            change['file_path'] = file_path
            change['absolute_path'] = os.path.join(repo_path, file_path)
            
            # Add diff preview for modifications
            if change['action'] == 'modify':
                try:
                    existing_path = Path(repo_path) / file_path
                    if existing_path.exists():
                        async with aiofiles.open(existing_path, 'r') as f:
                            original_content = await f.read()
                        
                        # Simple diff preview (first 200 chars of change)
                        new_content = change.get('content', '')
                        if original_content != new_content:
                            change['diff'] = f"Original: {len(original_content)} chars -> New: {len(new_content)} chars"
                        else:
                            change['diff'] = "No changes detected"
                except Exception:
                    change['diff'] = "Could not generate diff"
            
            validated_changes.append(change)
        
        return validated_changes
    
    async def _query_ai(self, prompt: str, system_message: str = None) -> str:
        """Query the AI model (Ollama or OpenAI)"""
        
        # Try OpenAI first if available
        if self.openai_client and self.model.startswith('gpt'):
            try:
                messages = []
                if system_message:
                    messages.append({"role": "system", "content": system_message})
                messages.append({"role": "user", "content": prompt})
                
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=4000,
                    temperature=0.1
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                print(f"OpenAI API error: {e}, falling back to Ollama")
        
        # Use Ollama for local models
        try:
            return await self._query_ollama(prompt, system_message)
        except Exception as e:
            raise Exception(f"Failed to query AI model: {str(e)}")
    
    async def _query_ollama(self, prompt: str, system_message: str = None) -> str:
        """Query Ollama API"""
        
        full_prompt = prompt
        if system_message:
            full_prompt = f"{system_message}\\n\\n{prompt}"
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 4000
            }
        }
        
        try:
            # Use asyncio for the HTTP request
            import httpx
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result.get('response', '')
                
        except Exception as e:
            raise Exception(f"Ollama API error: {str(e)}")
