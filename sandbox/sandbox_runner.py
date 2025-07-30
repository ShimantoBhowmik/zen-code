"""
Sandbox Runner for secure code execution
Handles repository cloning, change application, and cleanup with validation
"""

import os
import shutil
import asyncio
import tempfile
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import git
from git import Repo
import aiofiles
from rich.console import Console

console = Console()

class CodeValidator:
    """Validates generated code by running it and checking outputs"""
    
    def __init__(self, repo_path: str, working_dir: str = None):
        self.repo_path = repo_path
        self.max_iterations = 3
        
        # Create a dedicated validation workspace
        if working_dir:
            self.working_dir = os.path.join(working_dir, 'validation')
        else:
            home_dir = os.path.expanduser("~")
            self.working_dir = os.path.join(home_dir, '.shimu-code', 'validation')
        
        Path(self.working_dir).mkdir(parents=True, exist_ok=True, mode=0o755)
        
        # Create sample data directory for testing
        self.sample_data_dir = os.path.join(self.working_dir, 'sample_data')
        Path(self.sample_data_dir).mkdir(parents=True, exist_ok=True, mode=0o755)
        
        console.print(f"[dim]🔬 Validation workspace: {self.working_dir}[/dim]")
    
    async def validate_changes(self, changes: List[Dict], prompt: str) -> Tuple[bool, str, List[Dict]]:
        """
        Validate the generated changes by running the code and checking output
        Returns (success, feedback, corrected_changes)
        """
        console.print("🔍 [yellow]Validating generated code...[/yellow]")
        
        iteration = 1
        current_changes = changes
        last_error = ""
        
        while iteration <= self.max_iterations:
            console.print(f"📝 [cyan]Validation attempt {iteration}/{self.max_iterations}[/cyan]")
            
            # Apply changes temporarily for testing
            backup_files = await self._backup_existing_files(current_changes)
            await self._apply_temporary_changes(current_changes)
            
            # Run validation tests
            validation_result = await self._run_validation_tests(current_changes, prompt)
            
            # Restore original files
            await self._restore_backup_files(backup_files)
            
            if validation_result["success"]:
                console.print("✅ [green]Code validation successful![/green]")
                return True, validation_result["output"], current_changes
            
            last_error = validation_result["error"]
            console.print(f"❌ [red]Validation failed: {last_error}[/red]")
            
            if iteration == self.max_iterations:
                console.print("⚠️ [yellow]Max iterations reached. Using best attempt with fixes...[/yellow]")
                # Apply basic fixes as last resort
                final_changes = self._apply_basic_fixes(current_changes, last_error)
                return False, last_error, final_changes
            
            # Get AI feedback and corrections
            console.print("🤖 [blue]Getting AI feedback for corrections...[/blue]")
            corrected_changes = await self._get_corrected_changes(
                current_changes, 
                last_error, 
                prompt
            )
            
            # Check if we got meaningful corrections
            if corrected_changes == current_changes:
                console.print("⚠️ [yellow]No meaningful corrections received, applying basic fixes...[/yellow]")
                current_changes = self._apply_basic_fixes(current_changes, last_error)
            else:
                current_changes = corrected_changes
            
            iteration += 1
        
        return False, last_error, current_changes
    
    async def _backup_existing_files(self, changes: List[Dict]) -> Dict[str, str]:
        """Backup existing files that will be modified"""
        backups = {}
        for change in changes:
            # For validation, we create copies in working directory instead of modifying originals
            file_path = os.path.join(self.repo_path, change.get("file_path", ""))
            if os.path.exists(file_path):
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    backups[file_path] = await f.read()
        return backups
    
    async def _restore_backup_files(self, backups: Dict[str, str]):
        """Restore backed up files"""
        for file_path, content in backups.items():
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
    
    async def _apply_temporary_changes(self, changes: List[Dict]):
        """Apply changes temporarily for testing in the actual repository"""
        # Copy existing data files from repo to working directory for validation
        await self._copy_repo_data_files()
        
        for change in changes:
            action = change.get("action")
            file_path = change.get("file_path", "")
            
            if action in ["create", "modify"]:
                content = change.get("content", "")
                
                # Create validation files in working directory with repo data available
                validation_file_path = os.path.join(self.working_dir, os.path.basename(file_path))
                
                # Ensure proper file permissions
                async with aiofiles.open(validation_file_path, 'w', encoding='utf-8') as f:
                    await f.write(content)
                
                # Set proper permissions
                os.chmod(validation_file_path, 0o644)
    
    async def _copy_repo_data_files(self):
        """Copy existing data files from repository to working directory for validation"""
        # Clear previous validation files first
        for file in Path(self.working_dir).glob('*'):
            if file.is_file():
                file.unlink()
        
        # Common data file extensions to copy
        data_extensions = ['.csv', '.json', '.txt', '.xml', '.yaml', '.yml', '.tsv', '.log']
        
        try:
            # Walk through the repository and copy data files
            for root, dirs, files in os.walk(self.repo_path):
                # Skip hidden directories and common build/cache directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'build', 'dist']]
                
                for file in files:
                    if any(file.lower().endswith(ext) for ext in data_extensions):
                        src_path = os.path.join(root, file)
                        dst_path = os.path.join(self.working_dir, file)
                        
                        # Copy the file
                        try:
                            async with aiofiles.open(src_path, 'r', encoding='utf-8') as src:
                                content = await src.read()
                            async with aiofiles.open(dst_path, 'w', encoding='utf-8') as dst:
                                await dst.write(content)
                            
                            console.print(f"[dim]📄 Copied data file: {file}[/dim]")
                        except Exception as e:
                            # Try binary mode for files that might not be text
                            try:
                                async with aiofiles.open(src_path, 'rb') as src:
                                    content = await src.read()
                                async with aiofiles.open(dst_path, 'wb') as dst:
                                    await dst.write(content)
                                console.print(f"[dim]📄 Copied binary data file: {file}[/dim]")
                            except Exception as binary_error:
                                console.print(f"[dim]⚠️ Failed to copy {file}: {str(e)}[/dim]")
            
            # If no data files found, create minimal sample data as fallback
            data_files = list(Path(self.working_dir).glob('*'))
            if not data_files:
                console.print("[dim]📄 No data files found in repository, creating minimal samples...[/dim]")
                await self._create_minimal_sample_data()
                
        except Exception as e:
            console.print(f"[dim]⚠️ Error copying repo files: {str(e)}, creating sample data...[/dim]")
            await self._create_minimal_sample_data()
    
    async def _create_minimal_sample_data(self):
        """Create minimal sample data files as fallback"""
        # Create a basic CSV file
        csv_content = "name,salary,department\nJohn Doe,50000,Engineering\nJane Smith,60000,Marketing\nBob Johnson,55000,Engineering\nAlice Brown,65000,Sales\n"
        async with aiofiles.open(os.path.join(self.working_dir, 'data.csv'), 'w') as f:
            await f.write(csv_content)
        
        # Create a basic JSON file
        json_content = '{"employees": [{"name": "John", "salary": 50000}, {"name": "Jane", "salary": 60000}]}'
        async with aiofiles.open(os.path.join(self.working_dir, 'data.json'), 'w') as f:
            await f.write(json_content)
    
    async def _run_validation_tests(self, changes: List[Dict], prompt: str) -> Dict:
        """Run validation tests on the generated code"""
        try:
            # Find executable files to test in working directory
            for change in changes:
                original_file_path = change.get("file_path", "")
                # Use basename for working directory
                working_file_path = os.path.join(self.working_dir, os.path.basename(original_file_path))
                
                if working_file_path.endswith('.py'):
                    return await self._validate_python_code(working_file_path, prompt)
                elif working_file_path.endswith('.js'):
                    return await self._validate_javascript_code(working_file_path, prompt)
                elif working_file_path.endswith(('.html', '.htm')):
                    return await self._validate_html_code(working_file_path, prompt)
            
            return {"success": True, "output": "No executable code to validate", "error": None}
            
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}
    
    async def _validate_python_code(self, file_path: str, prompt: str) -> Dict:
        """Validate Python code by running it in the working directory"""
        try:
            # First check syntax
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                code = await f.read()
            
            try:
                compile(code, file_path, 'exec')
            except SyntaxError as e:
                return {"success": False, "output": "", "error": f"Syntax error: {str(e)}"}
            
            # Run the code and capture output in working directory
            result = await asyncio.create_subprocess_exec(
                'python', os.path.basename(file_path),  # Use basename since we're in working dir
                cwd=self.working_dir,  # Run in working directory with sample data
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, 'PYTHONPATH': self.working_dir}  # Set Python path
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=15)  # Increased timeout
                stdout = stdout.decode('utf-8')
                stderr = stderr.decode('utf-8')
            except asyncio.TimeoutError:
                result.kill()
                return {"success": False, "output": "", "error": "Code execution timed out (15s limit)"}
            
            if result.returncode != 0:
                # Provide more helpful error messages for common issues
                error_msg = stderr
                if "I/O operation on closed file" in stderr:
                    error_msg = f"File I/O error: {stderr}\nHint: Make sure files are properly opened and closed, or use 'with' statements for file handling. Check that your code is properly indented inside the 'with' block."
                elif "No such file or directory" in stderr:
                    error_msg = f"File not found error: {stderr}\nHint: The validation system has created sample data files (CSV, JSON, TXT) in the working directory. Check if your file references match available files."
                elif "ModuleNotFoundError" in stderr:
                    error_msg = f"Missing module: {stderr}\nHint: The code requires additional Python packages to be installed."
                elif "IndentationError" in stderr:
                    error_msg = f"Indentation error: {stderr}\nHint: Check that your code blocks are properly indented, especially inside 'with' statements and function definitions."
                elif "permission denied" in stderr.lower():
                    error_msg = f"Permission error: {stderr}\nHint: The file may not have proper permissions. This has been automatically fixed."
                
                return {
                    "success": False, 
                    "output": stdout, 
                    "error": f"Runtime error: {error_msg}"
                }
            
            # Check if output matches expected behavior from prompt
            expected_output = self._extract_expected_output(prompt)
            if expected_output and expected_output.lower() not in stdout.lower():
                return {
                    "success": False,
                    "output": stdout,
                    "error": f"Expected output '{expected_output}' not found in actual output: '{stdout.strip()}'"
                }
            
            console.print(f"[dim]✅ Python code executed successfully. Output: {stdout.strip()[:100]}...[/dim]")
            return {"success": True, "output": stdout, "error": None}
            
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}
    
    async def _validate_javascript_code(self, file_path: str, prompt: str) -> Dict:
        """Validate JavaScript code using Node.js in the working directory"""
        try:
            result = await asyncio.create_subprocess_exec(
                'node', os.path.basename(file_path),  # Use basename since we're in working dir
                cwd=self.working_dir,  # Run in working directory with sample data
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=15)  # Increased timeout
                stdout = stdout.decode('utf-8')
                stderr = stderr.decode('utf-8')
            except asyncio.TimeoutError:
                result.kill()
                return {"success": False, "output": "", "error": "Code execution timed out (15s limit)"}
            
            if result.returncode != 0:
                error_msg = stderr
                if "ENOENT" in stderr:
                    error_msg = f"File not found error: {stderr}\nHint: The validation system has created sample data files (CSV, JSON, TXT) in the working directory. Check if your file references match available files."
                elif "SyntaxError" in stderr:
                    error_msg = f"JavaScript syntax error: {stderr}\nHint: Check your JavaScript syntax, including proper use of brackets, semicolons, and variable declarations."
                
                return {
                    "success": False, 
                    "output": stdout, 
                    "error": f"JavaScript runtime error: {error_msg}"
                }
            
            expected_output = self._extract_expected_output(prompt)
            if expected_output and expected_output.lower() not in stdout.lower():
                return {
                    "success": False,
                    "output": stdout,
                    "error": f"Expected output '{expected_output}' not found in actual output: '{stdout.strip()}'"
                }
            
            console.print(f"[dim]✅ JavaScript code executed successfully. Output: {stdout.strip()[:100]}...[/dim]")
            return {"success": True, "output": stdout, "error": None}
            
        except FileNotFoundError:
            return {"success": False, "output": "", "error": "Node.js not found. Please install Node.js to validate JavaScript"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}
    
    async def _validate_html_code(self, file_path: str, prompt: str) -> Dict:
        """Basic HTML validation"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Basic HTML structure checks
            if '<html>' in content.lower() and '</html>' in content.lower():
                return {"success": True, "output": "Valid HTML structure", "error": None}
            elif '<!DOCTYPE html>' in content or '<html' in content:
                return {"success": True, "output": "Valid HTML5 structure", "error": None}
            else:
                return {"success": False, "output": "", "error": "Invalid HTML structure - missing html tags"}
                
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}
    
    def _extract_expected_output(self, prompt: str) -> Optional[str]:
        """Extract expected output from the prompt"""
        prompt_lower = prompt.lower()
        
        # Common patterns to look for
        if 'hello world' in prompt_lower or 'hello, world' in prompt_lower:
            return 'hello world'
        
        # Look for quoted strings that should be printed
        import re
        print_patterns = [
            r'print[s]?\s*["\']([^"\']+)["\']',
            r'output[s]?\s*["\']([^"\']+)["\']',
            r'display[s]?\s*["\']([^"\']+)["\']',
            r'console\.log\s*\(["\']([^"\']+)["\']\)'
        ]
        
        for pattern in print_patterns:
            match = re.search(pattern, prompt_lower)
            if match:
                return match.group(1)
        
        return None
    
    async def _get_corrected_changes(self, changes: List[Dict], error: str, original_prompt: str) -> List[Dict]:
        """Get corrected changes from AI based on validation error"""
        try:
            from agent.ai_agent import AIAgent
            
            ai_agent = AIAgent()
            
            correction_prompt = f"""
            The following code changes failed validation with this error: {error}
            
            Original request: {original_prompt}
            
            Current code that failed:
            {self._format_changes_for_prompt(changes)}
            
            Please provide corrected code that will:
            1. Fix the validation error
            2. Run successfully without syntax or runtime errors
            3. Produce the expected output as described in the original request
            4. Pay special attention to proper indentation, especially inside 'with' blocks
            
            Return the corrected changes in the same JSON format.
            """
            
            # Try to get AI corrections
            try:
                # Use the analyze method first, then generate changes
                analysis = await ai_agent.analyze_codebase(self.repo_path, correction_prompt)
                corrected_changes = await ai_agent.generate_changes(self.repo_path, correction_prompt, analysis)
                
                if corrected_changes and len(corrected_changes) > 0:
                    console.print(f"🔧 [green]AI provided {len(corrected_changes)} corrected changes[/green]")
                    return corrected_changes
                else:
                    console.print("⚠️ [yellow]AI correction returned empty results[/yellow]")
                    return self._apply_basic_fixes(changes, error)
                    
            except Exception as ai_error:
                if "404" in str(ai_error) or "Ollama" in str(ai_error):
                    console.print("⚠️ [yellow]Ollama not available, applying basic code fixes...[/yellow]")
                else:
                    console.print(f"⚠️ [yellow]AI correction failed: {str(ai_error)}[/yellow]")
                
                # Apply basic fixes when AI is not available
                return self._apply_basic_fixes(changes, error)
                
        except Exception as e:
            console.print(f"❌ [red]Failed to get AI corrections: {str(e)}[/red]")
            return self._apply_basic_fixes(changes, error)
    
    def _apply_basic_fixes(self, changes: List[Dict], error: str) -> List[Dict]:
        """Apply basic code fixes when AI correction is not available"""
        console.print("🔧 [cyan]Applying basic automatic fixes...[/cyan]")
        
        fixed_changes = []
        for change in changes:
            if change.get('file_path', '').endswith('.py'):
                fixed_content = self._fix_python_indentation(change.get('content', ''), error)
                fixed_change = change.copy()
                fixed_change['content'] = fixed_content
                fixed_changes.append(fixed_change)
            else:
                fixed_changes.append(change)
        
        return fixed_changes
    
    def _fix_python_indentation(self, code: str, error: str) -> str:
        """Apply basic Python indentation fixes"""
        if "I/O operation on closed file" in error:
            # Common fix: ensure code after 'with' statement is properly indented
            lines = code.split('\n')
            fixed_lines = []
            in_with_block = False
            
            for i, line in enumerate(lines):
                if line.strip().startswith('with ') and line.strip().endswith(':'):
                    in_with_block = True
                    fixed_lines.append(line)
                elif in_with_block and line.strip() and not line.startswith('    '):
                    # This line should be indented inside the with block
                    if line.strip() and not line.startswith('#'):
                        fixed_lines.append('    ' + line.lstrip())
                    else:
                        fixed_lines.append(line)
                else:
                    if in_with_block and line.strip() == '':
                        # Empty line in with block
                        fixed_lines.append(line)
                    elif in_with_block and line and not line.startswith('    ') and not line.startswith('\t'):
                        # End of with block
                        in_with_block = False
                        fixed_lines.append(line)
                    else:
                        fixed_lines.append(line)
            
            fixed_code = '\n'.join(fixed_lines)
            console.print("🔧 [green]Applied automatic indentation fix for 'with' statement[/green]")
            return fixed_code
        
        return code
    
    def _format_changes_for_prompt(self, changes: List[Dict]) -> str:
        """Format changes for inclusion in AI prompt"""
        formatted = []
        for change in changes:
            formatted.append(f"File: {change.get('file_path', 'unknown')}")
            formatted.append(f"Action: {change.get('action', 'unknown')}")
            formatted.append(f"Content:\n{change.get('content', '')}\n")
        return "\n".join(formatted)

class SandboxRunner:
    def __init__(self):
        # Use a more reliable sandbox location
        home_dir = os.path.expanduser("~")
        self.sandbox_base = os.path.join(home_dir, '.shimu-code', 'sandbox')
        self.sandbox_dir = os.getenv('SANDBOX_DIR', self.sandbox_base)
        self.max_repo_size_mb = int(os.getenv('MAX_REPO_SIZE_MB', '100'))
        self.current_repo_path = None
        self.working_dir = None  # For validation tests
        
        # Ensure sandbox directory exists with proper permissions
        Path(self.sandbox_dir).mkdir(parents=True, exist_ok=True, mode=0o755)
        
        # Create a dedicated working directory for code validation
        self.working_dir = os.path.join(self.sandbox_dir, 'working')
        Path(self.working_dir).mkdir(parents=True, exist_ok=True, mode=0o755)
        
        console.print(f"[dim]📁 Sandbox initialized at: {self.sandbox_dir}[/dim]")
    
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
    
    async def apply_changes(self, repo_path: str, changes: List[Dict[str, Any]], prompt: str = "", validate_code: bool = True):
        """
        Apply the generated code changes to the repository with optional validation
        Returns: (success: bool, validation_feedback: str)
        """
        try:
            final_changes = changes
            validation_success = True
            validation_feedback = ""
            
            # Run validation if enabled
            if validate_code and prompt:
                console.print("🔍 [cyan]Running code validation...[/cyan]")
                validator = CodeValidator(repo_path)
                success, feedback, validated_changes = await validator.validate_changes(changes, prompt)
                
                validation_success = success
                validation_feedback = feedback
                
                if success:
                    console.print("✅ [green]Code validation passed![/green]")
                else:
                    console.print(f"❌ [red]Code validation failed: {feedback}[/red]")
                    console.print("� [red]Cannot proceed with PR creation due to validation failures.[/red]")
                    return False, feedback
                
                final_changes = validated_changes
            
            # Apply the changes
            applied_changes = []
            
            for change in final_changes:
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
                
            console.print(f"✅ [green]Applied {len(applied_changes)} changes:[/green]")
            for change in applied_changes:
                console.print(f"  - {change}")
                
            return validation_success, validation_feedback
                
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
