#!/usr/bin/env python3
"""
Backspace CLI - Sandboxed AI Coding Agent
A command-line tool that accepts a GitHub repository URL and a natural language prompt,
then uses AI to make code changes and create a pull request.
"""

import os
import sys
import asyncio
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from agent.ai_agent import AIAgent
from sandbox.sandbox_runner import SandboxRunner
from utils.github import GitHubManager
from api.sse_client import SSEClient

console = Console()

def generate_concise_pr_title(prompt: str, changes: list) -> str:
    """Generate a concise PR title based on changes and prompt"""
    
    # Extract key actions from changes
    actions = set()
    files_count = len(changes)
    main_files = []
    
    for change in changes:
        actions.add(change['action'])
        file_path = change['file_path']
        # Get just the filename for key files
        if '/' in file_path:
            filename = file_path.split('/')[-1]
        else:
            filename = file_path
        main_files.append(filename)
    
    # Limit to 3 most important files
    if len(main_files) > 3:
        main_files = main_files[:2] + [f"and {len(main_files)-2} more"]
    
    # Create action summary
    if len(actions) == 1:
        action_text = list(actions)[0].title()
    elif "create" in actions and "modify" in actions:
        action_text = "Add & Update"
    elif "create" in actions:
        action_text = "Add"
    elif "modify" in actions:
        action_text = "Update"
    else:
        action_text = "Fix"
    
    # Generate short title based on prompt keywords
    prompt_lower = prompt.lower()
    if any(word in prompt_lower for word in ['fix', 'bug', 'error', 'issue']):
        category = "Fix"
    elif any(word in prompt_lower for word in ['add', 'create', 'new', 'implement']):
        category = "Add"
    elif any(word in prompt_lower for word in ['update', 'improve', 'enhance', 'refactor']):
        category = "Update"
    elif any(word in prompt_lower for word in ['test', 'testing']):
        category = "Test"
    elif any(word in prompt_lower for word in ['doc', 'readme', 'comment']):
        category = "Docs"
    else:
        category = action_text
    
    # Extract key subject from prompt (first 3-5 words)
    words = prompt.split()
    if len(words) > 5:
        subject = ' '.join(words[:4]) + "..."
    else:
        subject = prompt
    
    # Create final title (max 50 characters for GitHub best practices)
    if files_count == 1:
        title = f"{category}: {main_files[0]}"
    elif files_count <= 3:
        title = f"{category}: {', '.join(main_files)}"
    else:
        title = f"{category}: {files_count} files"
    
    # If title is still too long, use subject instead
    if len(title) > 50:
        title = f"{category}: {subject}"
        if len(title) > 50:
            title = title[:47] + "..."
    
    return title

@click.command()
@click.option(
    '--repo-url', 
    required=True, 
    help='GitHub repository URL to modify'
)
@click.option(
    '--prompt', 
    required=True, 
    help='Natural language description of changes to make'
)
@click.option(
    '--model', 
    default=None, 
    help='AI model to use (default: from DEFAULT_MODEL env var)'
)
@click.option(
    '--branch', 
    default=None, 
    help='Target branch name (auto-generated if not provided)'
)
@click.option(
    '--dry-run', 
    is_flag=True, 
    help='Show what would be done without making actual changes'
)
def main(repo_url: str, prompt: str, model: str, branch: str, dry_run: bool):
    """
    Backspace CLI - AI-powered code modification tool
    
    Examples:
        python cli.py --repo-url https://github.com/user/repo --prompt "Add a login page"
        python cli.py --repo-url https://github.com/user/repo --prompt "Fix the authentication bug" --model codellama
    """
    # Use model from environment if not specified
    if model is None:
        model = os.getenv('DEFAULT_MODEL', 'codellama')
    
    # Validate environment
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token or github_token == 'your_personal_access_token_here':
        console.print("❌ [red]GitHub token not configured. Please set GITHUB_TOKEN in .env file[/red]")
        console.print("Generate a token at: https://github.com/settings/tokens")
        sys.exit(1)
    
    # Parse repository URL
    try:
        repo_parts = repo_url.replace('https://github.com/', '').split('/')
        if len(repo_parts) < 2:
            raise ValueError("Invalid repository URL format")
        owner, repo_name = repo_parts[0], repo_parts[1]
    except Exception as e:
        console.print(f"❌ [red]Invalid repository URL: {repo_url}[/red]")
        sys.exit(1)
    
    console.print(f"🚀 [bold blue]Backspace CLI - AI Coding Agent[/bold blue]")
    console.print(f"📂 Repository: {owner}/{repo_name}")
    console.print(f"💬 Prompt: {prompt}")
    console.print(f"🤖 Model: {model}")
    
    if dry_run:
        console.print("🔍 [yellow]DRY RUN MODE - No actual changes will be made[/yellow]")
    
    # Run the main process
    asyncio.run(process_repository(
        repo_url=repo_url,
        owner=owner,
        repo_name=repo_name,
        prompt=prompt,
        model=model,
        branch=branch,
        dry_run=dry_run
    ))

async def process_repository(repo_url: str, owner: str, repo_name: str, 
                           prompt: str, model: str, branch: str, dry_run: bool, validate_code: bool = True):
    """Main processing pipeline with enhanced progress tracking and validation"""
    
    # Import progress system
    from progress_display import EnhancedProgressCallback, create_celebration_display, create_error_display, create_failure_display
    
    progress_callback = EnhancedProgressCallback()
    
    try:
        # Initialize components
        sandbox = SandboxRunner()
        ai_agent = AIAgent(model=model)
        github_manager = GitHubManager(owner=owner, repo_name=repo_name)
        
        # Start progress display
        await progress_callback.start_progress()
        
        # Step 1: Clone repository
        await progress_callback.on_clone_start(repo_url)
        try:
            repo_path = await sandbox.clone_repository(repo_url)
            # Get repository size for display
            import os
            total_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                           for dirpath, dirnames, filenames in os.walk(repo_path)
                           for filename in filenames)
            size_mb = total_size / (1024 * 1024)
            await progress_callback.on_clone_complete(repo_path, size_mb)
        except Exception as e:
            await progress_callback.on_error("clone", str(e))
            raise e
        
        # Step 2: Analyze codebase
        await progress_callback.on_analyze_start()
        try:
            analysis = await ai_agent.analyze_codebase(repo_path, prompt)
            file_count = len(analysis.get('structure', {}).get('files', []))
            analysis_summary = analysis.get('summary', 'Analysis complete')
            await progress_callback.on_analyze_complete(file_count, analysis_summary)
        except Exception as e:
            await progress_callback.on_error("analyze", str(e))
            raise e
        
        # Step 3: Generate code changes
        await progress_callback.on_generate_start()
        try:
            changes = await ai_agent.generate_changes(repo_path, prompt, analysis)
            await progress_callback.on_generate_complete(len(changes))
            
            # Show changes in dry-run mode
            if dry_run:
                await progress_callback.stop_progress()
                console.print("\n🔍 [bold yellow]Proposed Changes (Dry Run):[/bold yellow]")
                for change in changes:
                    console.print(f"  📄 {change['file_path']}")
                    console.print(f"     Action: {change['action']}")
                    if change.get('diff'):
                        console.print(f"     Preview: {change['diff'][:100]}...")
                return
                
        except Exception as e:
            await progress_callback.on_error("generate", str(e))
            raise e
        
        # Step 4: Apply changes with validation
        await progress_callback.on_apply_start(len(changes))
        try:
            validation_success, validation_feedback = await sandbox.apply_changes(repo_path, changes, prompt, validate_code=validate_code)
            applied_changes = [f"{change['action'].title()}: {change['file_path']}" for change in changes]
            await progress_callback.on_apply_complete(applied_changes)
            
            # If validation failed, stop here and show failure
            if not validation_success:
                await progress_callback.stop_progress()
                await sandbox.cleanup()
                create_failure_display(validation_feedback)
                return
                
        except Exception as e:
            await progress_callback.on_error("apply", str(e))
            raise e
        
        # Step 5: Create branch and commit
        await progress_callback.on_commit_start(branch)
        try:
            if not branch:
                branch = f"zen-code-{int(asyncio.get_event_loop().time())}"
            
            commit_sha = await github_manager.create_branch_and_commit(
                repo_path, branch, f"🤖 ZEN CODE: {prompt}", changes
            )
            await progress_callback.on_commit_complete(branch, commit_sha)
        except Exception as e:
            await progress_callback.on_error("commit", str(e))
            raise e
        
        # Step 6: Push to GitHub
        await progress_callback.on_push_start(branch)
        try:
            # Push is handled in create_branch_and_commit, so just mark as complete
            await progress_callback.on_push_complete(branch)
        except Exception as e:
            await progress_callback.on_error("push", str(e))
            raise e
        
        # Step 7: Create pull request
        await progress_callback.on_pr_start()
        try:
            # Generate concise PR title
            pr_title = generate_concise_pr_title(prompt, changes)
            
            pr_url = await github_manager.create_pull_request(
                branch=branch,
                title=pr_title,
                body=f"## AI-Generated Changes by ZEN CODE\n\n"
                     f"**Original Request:** {prompt}\n\n"
                     f"**AI Model:** {model}\n\n"
                     f"**Changes Made:**\n" + 
                     "\n".join([f"- {change['action'].title()}: `{change['file_path']}`" for change in changes]) +
                     f"\n\n---\n*Generated automatically by ZEN CODE✨*"
            )
            await progress_callback.on_pr_complete(pr_url)
        except Exception as e:
            await progress_callback.on_error("pr", str(e))
            raise e
        
        # Stop progress display
        await progress_callback.stop_progress()
        
        # Cleanup sandbox before showing success
        await sandbox.cleanup()
        
        # Show success celebration
        create_celebration_display(pr_url)
        
    except Exception as e:
        # Stop progress display and show error
        await progress_callback.stop_progress()
        create_error_display(str(e))
        # Cleanup sandbox on error too
        await sandbox.cleanup()
        sys.exit(1)

if __name__ == '__main__':
    main()
