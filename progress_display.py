"""
Enhanced progress visualization for ZEN CODE
Provides beautiful progress bars, status updates, and real-time feedback
"""

import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn, 
    TaskProgressColumn, TimeRemainingColumn, TimeElapsedColumn
)
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.align import Align
import threading

console = Console()

class ZenProgressTracker:
    """Advanced progress tracking with beautiful visualizations"""
    
    def __init__(self):
        self.steps = [
            {"id": "clone", "name": "Cloning Repository", "status": "pending"},
            {"id": "analyze", "name": "Analyzing Codebase", "status": "pending"},
            {"id": "generate", "name": "Generating Changes", "status": "pending"},
            {"id": "apply", "name": "Applying Changes", "status": "pending"},
            {"id": "commit", "name": "Creating Branch & Commit", "status": "pending"},
            {"id": "push", "name": "Pushing to GitHub", "status": "pending"},
            {"id": "pr", "name": "Creating Pull Request", "status": "pending"}
        ]
        self.current_step = 0
        self.details = {}
        self.start_time = time.time()
        
    def update_step_status(self, step_id: str, status: str, details: str = ""):
        """Update the status of a specific step"""
        for step in self.steps:
            if step["id"] == step_id:
                step["status"] = status
                if details:
                    self.details[step_id] = details
                break
    
    def get_progress_table(self) -> Table:
        """Generate a beautiful progress table"""
        table = Table(title="ZEN CODE Progress", show_header=False, box=None)
        
        for i, step in enumerate(self.steps):
            if step["status"] == "completed":
                icon = "✅"
                style = "green"
            elif step["status"] == "running":
                icon = "⚡"
                style = "yellow"
            elif step["status"] == "error":
                icon = "❌"
                style = "red"
            else:
                icon = "⏳"
                style = "dim"
            
            step_text = f"{icon} {step['name']}"
            
            # Add details if available
            if step["id"] in self.details:
                details = self.details[step["id"]]
                step_text += f"\n   [dim]{details}[/dim]"
            
            table.add_row(f"[{style}]{step_text}[/{style}]")
        
        return table
    
    def get_summary_panel(self) -> Panel:
        """Generate a summary panel with overall progress"""
        completed = len([s for s in self.steps if s["status"] == "completed"])
        total = len(self.steps)
        elapsed = time.time() - self.start_time
        
        progress_bar = "█" * (completed * 20 // total) + "░" * (20 - (completed * 20 // total))
        
        summary = f"""
[bold cyan]Overall Progress:[/bold cyan] {completed}/{total} steps completed
[bold cyan]Progress Bar:[/bold cyan] [{progress_bar}] {(completed/total)*100:.1f}%
[bold cyan]Elapsed Time:[/bold cyan] {elapsed:.1f}s
[bold cyan]Status:[/bold cyan] {'🎉 Complete!' if completed == total else '🔄 In Progress...'}
"""
        
        return Panel(
            summary.strip(),
            title="📊 Execution Summary",
            border_style="bright_blue"
        )

class AnimatedProgress:
    """Animated progress display with live updates"""
    
    def __init__(self):
        self.tracker = ZenProgressTracker()
        self.live = None
        self.running = False
    
    def start(self):
        """Start the animated progress display"""
        self.running = True
        
        def render_display():
            table = self.tracker.get_progress_table()
            return table
        
        # Use Live with simple table display
        self.live = Live(render_display(), refresh_per_second=2, console=console)
        self.live.start()
        
        # Start a background thread to update the display
        def update_loop():
            while self.running:
                if self.live:
                    try:
                        self.live.update(self.tracker.get_progress_table())
                    except Exception:
                        pass  # Ignore update errors
                time.sleep(0.5)
        
        self.update_thread = threading.Thread(target=update_loop, daemon=True)
        self.update_thread.start()
    
    def stop(self):
        """Stop the animated progress display"""
        self.running = False
        if hasattr(self, 'update_thread'):
            self.update_thread.join(timeout=1.0)
        if self.live:
            self.live.stop()
    
    def update_step(self, step_id: str, status: str, details: str = ""):
        """Update a step's status"""
        self.tracker.update_step_status(step_id, status, details)

class EnhancedProgressCallback:
    """Enhanced progress callback for the main CLI"""
    
    def __init__(self):
        self.progress_display = AnimatedProgress()
        self.step_mapping = {
            "clone": "clone",
            "analyze": "analyze", 
            "generate": "generate",
            "apply": "apply",
            "commit": "commit",
            "push": "push",
            "pr": "pr"
        }
    
    async def start_progress(self):
        """Start the progress display"""
        self.progress_display.start()
    
    async def stop_progress(self):
        """Stop the progress display"""
        self.progress_display.stop()
    
    async def update_progress(self, step: str, status: str, details: str = ""):
        """Update progress for a specific step"""
        if step in self.step_mapping:
            self.progress_display.update_step(self.step_mapping[step], status, details)
    
    async def on_clone_start(self, repo_url: str):
        """Called when repository cloning starts"""
        await self.update_progress("clone", "running", f"Cloning {repo_url}")
    
    async def on_clone_complete(self, repo_path: str, size_mb: float):
        """Called when repository cloning completes"""
        await self.update_progress("clone", "completed", f"Cloned to {repo_path} ({size_mb:.1f}MB)")
    
    async def on_analyze_start(self):
        """Called when codebase analysis starts"""
        await self.update_progress("analyze", "running", "AI analyzing repository structure...")
    
    async def on_analyze_complete(self, file_count: int, analysis_summary: str):
        """Called when codebase analysis completes"""
        await self.update_progress("analyze", "completed", f"Analyzed {file_count} files - {analysis_summary[:50]}...")
    
    async def on_generate_start(self):
        """Called when code generation starts"""
        await self.update_progress("generate", "running", "AI generating code changes...")
    
    async def on_generate_complete(self, change_count: int):
        """Called when code generation completes"""
        await self.update_progress("generate", "completed", f"Generated {change_count} changes")
    
    async def on_apply_start(self, change_count: int):
        """Called when applying changes starts"""
        await self.update_progress("apply", "running", f"Applying {change_count} changes...")
    
    async def on_apply_complete(self, applied_changes: List[str]):
        """Called when applying changes completes"""
        change_summary = ", ".join(applied_changes[:3])
        if len(applied_changes) > 3:
            change_summary += f" and {len(applied_changes) - 3} more"
        await self.update_progress("apply", "completed", f"Applied: {change_summary}")
    
    async def on_commit_start(self, branch_name: str):
        """Called when commit process starts"""
        await self.update_progress("commit", "running", f"Creating branch '{branch_name}'...")
    
    async def on_commit_complete(self, branch_name: str, commit_hash: str):
        """Called when commit process completes"""
        await self.update_progress("commit", "completed", f"Branch '{branch_name}' created with commit {commit_hash[:8]}")
    
    async def on_push_start(self, branch_name: str):
        """Called when push starts"""
        await self.update_progress("push", "running", f"Pushing branch '{branch_name}' to GitHub...")
    
    async def on_push_complete(self, branch_name: str):
        """Called when push completes"""
        await self.update_progress("push", "completed", f"Successfully pushed '{branch_name}'")
    
    async def on_pr_start(self):
        """Called when PR creation starts"""
        await self.update_progress("pr", "running", "Creating pull request...")
    
    async def on_pr_complete(self, pr_url: str):
        """Called when PR creation completes"""
        await self.update_progress("pr", "completed", f"PR created: {pr_url}")
    
    async def on_error(self, step: str, error_message: str):
        """Called when an error occurs"""
        if step in self.step_mapping:
            await self.update_progress(self.step_mapping[step], "error", f"Error: {error_message[:50]}...")

def create_celebration_display(pr_url: str):
    """Create a celebration display for successful completion"""
    celebration = """

   ███████╗██╗   ██╗ ██████╗ ██████╗███████╗███████╗███████╗██╗
   ██╔════╝██║   ██║██╔════╝██╔════╝██╔════╝██╔════╝██╔════╝██║
   ███████╗██║   ██║██║     ██║     █████╗  ███████╗███████╗██║
   ╚════██║██║   ██║██║     ██║     ██╔══╝  ╚════██║╚════██║╚═╝
   ███████║╚██████╔╝╚██████╗╚██████╗███████╗███████║███████║██╗
   ╚══════╝ ╚═════╝  ╚═════╝ ╚═════╝╚══════╝╚══════╝╚══════╝╚═╝

"""
    
    success_panel = Panel(
        f"{celebration}\n\n"
        f"Your AI-generated changes are ready for review:\n"
        f"[bold cyan]{pr_url}[/bold cyan]\n\n"
        f"[yellow]What's next?[/yellow]\n"
        f"1. Review the changes in your GitHub repository\n"
        f"2. Test the generated code\n"
        f"3. Merge the pull request if everything looks good\n\n"
        f"[bold magenta]Thank you for using ZEN CODE!✨[/bold magenta]",
        title="SUCCESS",
        border_style="bright_green"
    )
    
    console.print(success_panel)

def create_failure_display(validation_feedback: str):
    """Create a validation failure display"""
    failure_panel = Panel(
f"[bold red]🚫 CODE VALIDATION FAILED[/bold red]\n\n"
f"[yellow]Validation Error:[/yellow]\n"
f"{validation_feedback}\n\n"
f"[red]❌ Pull Request NOT Created[/red]\n"
f"The generated code failed validation and cannot be deployed safely.\n\n"
f"[cyan]💡 What went wrong?[/cyan]\n"
f"• The AI-generated code has syntax or runtime errors\n"
f"• Code doesn't produce expected output\n"
f"• Missing dependencies or file references\n\n"
f"[cyan]🔧 Suggested Actions:[/cyan]\n"
f"1. Try rephrasing your request more specifically\n"
f"2. Include more context about expected behavior\n"
f"3. Check if all required files exist in the repository\n"
f"4. Try with a different AI model\n\n"
f"[dim]ZEN CODE ensures code quality by validating before deployment.[/dim]",
title="VALIDATION FAILURE",
border_style="bright_red"
    )
    
    console.print(Align.center(failure_panel))

def create_error_display(error_message: str):
    """Create an error display"""
    error_panel = Panel(
        f"[bold red]❌ Oops! Something went wrong[/bold red]\n\n"
        f"[yellow]Error Details:[/yellow]\n"
        f"{error_message}\n\n"
        f"[cyan]💡 Troubleshooting Tips:[/cyan]\n"
        f"1. Check your internet connection\n"
        f"2. Verify your GitHub token has the right permissions\n"
        f"3. Make sure Ollama is running (for local models)\n"
        f"4. Try again with a simpler prompt\n\n"
        f"[dim]If the problem persists, please check the documentation.[/dim]",
        title="⚠️  ERROR",
        border_style="bright_red"
    )
    
    console.print(Align.center(error_panel))

# Export the main progress callback class
__all__ = ['EnhancedProgressCallback', 'create_celebration_display', 'create_error_display', 'create_failure_display']
