"""
Interactive CLI interface for Backspace CLI
Provides a chat-like experience with ASCII art and guided prompts
"""

import os
import sys
import time
from typing import Optional, Dict, Any
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import click

console = Console()

def display_ascii_art():
    """Display the SHIMU CODE ASCII art"""
    ascii_art = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ███████╗██╗  ██╗██╗███╗   ███╗██╗   ██╗     ██████╗ ██████╗ ██████╗ ███████╗
║   ██╔════╝██║  ██║██║████╗ ████║██║   ██║    ██╔════╝██╔═══██╗██╔══██╗██╔════╝
║   ███████╗███████║██║██╔████╔██║██║   ██║    ██║     ██║   ██║██║  ██║█████╗  
║   ╚════██║██╔══██║██║██║╚██╔╝██║██║   ██║    ██║     ██║   ██║██║  ██║██╔══╝  
║   ███████║██║  ██║██║██║ ╚═╝ ██║╚██████╔╝    ╚██████╗╚██████╔╝██████╔╝███████╗
║   ╚══════╝╚═╝  ╚═╝╚═╝╚═╝     ╚═╝ ╚═════╝      ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝
╚═══════════════════════════════════════════════════════════════════╝
"""
    
    # Create a gradient effect for the ASCII art
    art_text = Text(ascii_art)
    art_text.stylize("bold cyan", 0, 200)
    art_text.stylize("bold blue", 200, 400)
    art_text.stylize("bold magenta", 400, 600)
    
    console.print(art_text)
    console.print()

def display_welcome_message():
    """Display welcome message and instructions"""
    welcome_panel = Panel.fit(
        "[bold green]Welcome to SHIMU CODE![/bold green]\n\n"
        "[cyan]What I can do for you:[/cyan]\n"
        "   • Analyze any GitHub repository\n"
        "   • Generate code changes from natural language\n"
        "   • Create pull requests automatically\n"
        "   • Support multiple programming languages\n\n"
        "[yellow]Let's build something amazing together![/yellow]",
        title="✨ AI Code Assistant ✨",
        border_style="bright_blue"
    )
    console.print(welcome_panel)
    console.print()

def get_repository_url() -> str:
    """Get repository URL with validation and suggestions"""
    console.print("[bold blue]Step 1: Repository Selection[/bold blue]")
    console.print("Enter the GitHub repository you'd like me to work with.")
    console.print("[dim]Examples: https://github.com/user/repo or user/repo[/dim]\n")
    
    while True:
        repo_url = Prompt.ask(
            "[cyan]Repository URL[/cyan]",
            default="",
            show_default=False
        )
        
        if not repo_url:
            console.print("[red]❌ Repository URL is required![/red]")
            continue
            
        # Auto-format repository URL
        if not repo_url.startswith('https://'):
            if '/' in repo_url and not repo_url.startswith('github.com'):
                repo_url = f"https://github.com/{repo_url}"
            elif not repo_url.startswith('github.com'):
                console.print("[red]❌ Invalid repository format. Please use: user/repo or full URL[/red]")
                continue
        
        # Validate URL format
        if 'github.com' not in repo_url:
            console.print("[red]❌ Only GitHub repositories are supported currently[/red]")
            continue
            
        console.print(f"[green]✅ Repository: {repo_url}[/green]\n")
        return repo_url

def get_coding_prompt() -> Dict[str, Any]:
    """Get coding prompt with guided questions and suggestions"""
    console.print("[bold blue]Step 2: Describe Your Vision[/bold blue]")
    console.print("Tell me what you'd like me to build, fix, or improve.")
    console.print("[dim]The more specific you are, the better results you'll get![/dim]\n")
    
    # Main prompt
    main_prompt = Prompt.ask(
        "[cyan]What would you like me to do?[/cyan]",
        default="",
        show_default=False
    )
    
    if not main_prompt:
        console.print("[red]❌ Please describe what you'd like me to do[/red]")
        return get_coding_prompt()
    
    # Additional context questions
    console.print("\n[bold blue]Let me gather some more details...[/bold blue]")
    
    # Project type
    project_types = [
        "Web Application", "API/Backend", "Library/Package", "CLI Tool", 
        "Mobile App", "Data Science", "Machine Learning", "Other"
    ]
    
    project_type_table = Table(title="", show_header=False)
    for i, ptype in enumerate(project_types, 1):
        project_type_table.add_row(f"[cyan]{i}[/cyan]", ptype)
    
    console.print(project_type_table)
    
    project_type_choice = Prompt.ask(
        "What type of project is this? (1-8)",
        choices=[str(i) for i in range(1, 9)],
        default="8",
        show_choices=False
    )
    
    selected_project_type = project_types[int(project_type_choice) - 1]
    
    # Programming language preference
    languages = [
        "Python", "JavaScript/TypeScript", "Java", "C#", "Go", 
        "Rust", "PHP", "Ruby", "Let AI decide"
    ]

    lang_table = Table(title="", show_header=False)
    for i, lang in enumerate(languages, 1):
        lang_table.add_row(f"[cyan]{i}[/cyan]", lang)
    
    console.print(lang_table)
    
    language_choice = Prompt.ask(
        "Primary programming language? (1-9)",
        choices=[str(i) for i in range(1, 10)],
        default="9",
        show_choices=False
    )
    
    selected_language = languages[int(language_choice) - 1]
    
    # Additional requirements
    additional_requirements = Prompt.ask(
        "[cyan]Any specific requirements or constraints?[/cyan]",
        default="None"
    )
    
    # Build enhanced prompt
    enhanced_prompt = build_enhanced_prompt(
        main_prompt, selected_project_type, selected_language, 
        additional_requirements
    )
    
    # Show summary
    summary_panel = Panel(
        f"[bold green]Task Summary[/bold green]\n\n"
        f"[cyan]Main Request:[/cyan] {main_prompt}\n"
        f"[cyan]Project Type:[/cyan] {selected_project_type}\n"
        f"[cyan]Language:[/cyan] {selected_language}\n"
        f"[cyan]Requirements:[/cyan] {additional_requirements}\n\n"
        f"[yellow]Enhanced Prompt:[/yellow]\n{enhanced_prompt}",
        title="Configuration",
        border_style="green"
    )
    console.print(summary_panel)
    
    confirm = Confirm.ask("\n[bold]Does this look correct?[/bold]", default=True)
    
    if not confirm:
        console.print("[yellow]Let's try again...[/yellow]\n")
        return get_coding_prompt()
    
    return {
        "main_prompt": main_prompt,
        "enhanced_prompt": enhanced_prompt,
        "project_type": selected_project_type,
        "language": selected_language,
        "requirements": additional_requirements
    }

def build_enhanced_prompt(main_prompt: str, project_type: str, language: str, 
                         requirements: str) -> str:
    """Build an enhanced prompt with XML context format"""
    
    # Language-specific guidelines
    language_guidelines = {
        "Python": [
            "Follow PEP 8 style guidelines for clean and readable code.",
            "Include type hints where applicable.",
            "Add descriptive docstrings for functions and classes.",
            "Use appropriate data structures and built-in functions."
        ],
        "JavaScript/TypeScript": [
            "Use modern ES6+ syntax and features.",
            "Follow TypeScript best practices if applicable.",
            "Include proper error handling with try-catch blocks.",
            "Use async/await for asynchronous operations."
        ],
        "Java": [
            "Follow Java coding conventions and naming standards.",
            "Use appropriate design patterns where beneficial.",
            "Include proper exception handling mechanisms.",
            "Write clean, object-oriented code with clear interfaces."
        ],
        "C#": [
            "Follow C# coding standards and conventions.",
            "Use LINQ where appropriate for data operations.",
            "Include proper exception handling and logging.",
            "Implement interfaces and abstract classes appropriately."
        ],
        "Go": [
            "Follow Go conventions and idioms.",
            "Use proper error handling with error values.",
            "Keep code simple, readable, and efficient.",
            "Use goroutines and channels for concurrency when needed."
        ],
        "Rust": [
            "Follow Rust best practices and idioms.",
            "Ensure memory safety with ownership and borrowing.",
            "Use proper error handling with Result and Option types.",
            "Write efficient, zero-cost abstractions."
        ],
        "PHP": [
            "Follow PSR standards for code formatting and structure.",
            "Use proper namespacing and autoloading.",
            "Include comprehensive error handling and validation.",
            "Follow modern PHP practices and avoid deprecated features."
        ],
        "Ruby": [
            "Follow Ruby conventions and idiomatic patterns.",
            "Use appropriate Ruby gems and standard library features.",
            "Include proper error handling with rescue blocks.",
            "Write clean, expressive code that reads like natural language."
        ],
        "Let AI decide": [
            "Choose the most appropriate language for the task.",
            "Follow the selected language's best practices and conventions.",
            "Ensure code is clean, readable, and well-documented.",
            "Use language-specific features effectively."
        ]
    }
    
    # Project-specific considerations
    project_guidelines = {
        "Web Application": [
            "Consider responsive design and cross-browser compatibility.",
            "Implement proper user authentication and authorization.",
            "Focus on user experience and accessibility.",
            "Ensure security best practices for web applications."
        ],
        "API/Backend": [
            "Design RESTful APIs with proper HTTP status codes.",
            "Implement authentication and rate limiting.",
            "Include comprehensive API documentation.",
            "Focus on scalability and performance optimization."
        ],
        "Library/Package": [
            "Design clean, intuitive APIs for end users.",
            "Include comprehensive documentation and examples.",
            "Implement proper versioning and backward compatibility.",
            "Add thorough testing and error handling."
        ],
        "CLI Tool": [
            "Focus on user experience with clear help documentation.",
            "Provide meaningful error messages and usage examples.",
            "Ensure cross-platform compatibility.",
            "Include proper command-line argument parsing."
        ],
        "Mobile App": [
            "Follow mobile-specific design patterns and guidelines.",
            "Optimize for performance and battery usage.",
            "Consider offline functionality and data synchronization.",
            "Implement proper navigation and user interface components."
        ],
        "Data Science": [
            "Focus on data processing efficiency and accuracy.",
            "Include data visualization and analysis components.",
            "Follow scientific computing best practices.",
            "Ensure reproducibility and proper data handling."
        ],
        "Machine Learning": [
            "Implement proper model training and evaluation pipelines.",
            "Include data preprocessing and feature engineering.",
            "Follow MLOps best practices for model deployment.",
            "Ensure model interpretability and performance monitoring."
        ],
        "Other": [
            "Apply general software engineering best practices.",
            "Focus on code maintainability and readability.",
            "Include appropriate testing and documentation.",
            "Consider scalability and performance implications."
        ]
    }
    
    # Get guidelines for the selected language and project type
    lang_guides = language_guidelines.get(language, language_guidelines["Let AI decide"])
    proj_guides = project_guidelines.get(project_type, project_guidelines["Other"])
    
    # Build the XML-formatted prompt
    enhanced_prompt = f"""<Prompt>
  <TaskSummary>
    <MainRequest>{main_prompt}</MainRequest>
    <ProjectType>{project_type}</ProjectType>
    <Language>{language}</Language>
    <Requirements>{requirements}</Requirements>
  </TaskSummary>

  <Context>
    <Description>
      {main_prompt} Ensure the solution follows industry best practices and is production-ready.
    </Description>
  </Context>

  <Guidelines>
    <CodeQuality>
""" + "\n".join([f"      <Item>{guide}</Item>" for guide in lang_guides]) + f"""
    </CodeQuality>
    <ProjectSpecific>
""" + "\n".join([f"      <Item>{guide}</Item>" for guide in proj_guides]) + f"""
    </ProjectSpecific>
    <General>
      <Item>Ensure the code is immediately executable without modification.</Item>
      <Item>Include comprehensive error handling and input validation.</Item>
      <Item>Write production-ready, maintainable code that can be easily extended.</Item>
      <Item>Add clear comments and documentation where helpful.</Item>
      <Item>Consider security implications and implement appropriate safeguards.</Item>
    </General>
  </Guidelines>

  <ExpectedOutput>
    <Description>
      Working {language.lower()} code for a {project_type.lower()} that implements: {main_prompt}
    </Description>
  </ExpectedOutput>
</Prompt>"""
    
    return enhanced_prompt

def generate_branch_name(prompt: str) -> str:
    """Generate a branch name based on the user's request"""
    import re
    import time
    
    # Extract key words from the prompt
    words = prompt.lower().split()
    
    # Filter out common words and keep meaningful ones
    stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'}
    
    meaningful_words = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Take first 2-3 most meaningful words
    key_words = meaningful_words[:3] if len(meaningful_words) >= 3 else meaningful_words[:2]
    
    # Clean words for branch name (alphanumeric and hyphens only)
    clean_words = []
    for word in key_words:
        clean_word = re.sub(r'[^a-zA-Z0-9]', '', word)
        if clean_word:
            clean_words.append(clean_word)
    
    # Create base branch name
    if clean_words:
        base_name = '-'.join(clean_words)
    else:
        base_name = 'shimu-code'
    
    # Add timestamp to ensure uniqueness
    timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
    
    # Create final branch name
    branch_name = f"shimu/{base_name}-{timestamp}"
    
    # Ensure it's not too long (GitHub branch name limit is 250 chars, but keep it reasonable)
    if len(branch_name) > 50:
        branch_name = f"shimu/{base_name[:30]}-{timestamp}"
    
    return branch_name

def get_available_models() -> list:
    """Get available models from Ollama only"""
    import subprocess
    import json
    
    available_models = []
    
    try:
        # Try to get Ollama models
        result = subprocess.run(
            ['ollama', 'list'], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # Skip header line and parse model names
            for line in lines[1:]:  # Skip "NAME SIZE MODIFIED" header
                if line.strip():
                    # Extract model name (first column)
                    model_name = line.split()[0]
                    if ':' in model_name:
                        available_models.append(model_name)
                    else:
                        # Add default tag if no tag specified
                        available_models.append(f"{model_name}:latest")
        
        if available_models:
            console.print(f"[dim]Found {len(available_models)} Ollama models[/dim]")
        else:
            console.print("[dim]No Ollama models found[/dim]")
        
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        console.print("[dim]Ollama not available or command failed[/dim]")
    
    # If no models found, provide a default fallback
    if not available_models:
        available_models = ["codellama:7b"]
        console.print("[dim]Using default fallback model[/dim]")
    
    return available_models

def get_execution_options(prompt_data: Dict[str, Any]) -> Dict[str, Any]:
    """Get execution options from user"""
    console.print("\n[bold blue]Step 3: Execution Options[/bold blue]")
    
    # Dry run option
    dry_run = Confirm.ask(
        "[cyan]Would you like to preview changes first (dry run)?[/cyan]",
        default=True
    )
    
    # Auto-generate branch name
    branch_name = generate_branch_name(prompt_data["main_prompt"])
    console.print(f"[dim]Auto-generated branch: {branch_name}[/dim]")
    
    # Model selection - get available models dynamically
    console.print("\n[dim]Detecting available AI models...[/dim]")
    available_models = get_available_models()
    default_model = os.getenv('DEFAULT_MODEL', available_models[0] if available_models else 'codellama:7b')

    model_table = Table(title="Available Models", show_header=False)
    for i, model in enumerate(available_models, 1):
        status = "(default)" if model == default_model else ""
        model_table.add_row(f"[cyan]{i}[/cyan]", f"{model} [dim]{status}[/dim]")
    
    console.print(model_table)
    
    model_choice = Prompt.ask(
        f"Select AI model (1-{len(available_models)})",
        choices=[str(i) for i in range(1, len(available_models) + 1)],
        default="1",
        show_choices=False
    )
    
    selected_model = available_models[int(model_choice) - 1]
    
    return {
        "dry_run": dry_run,
        "branch": branch_name,
        "model": selected_model
    }

def display_execution_summary(repo_url: str, prompt_data: Dict[str, Any], options: Dict[str, Any]):
    """Display execution summary before starting"""
    summary = Table(title="", show_header=False, box=None)
    summary.add_row("[cyan]Repository:[/cyan]", repo_url)
    summary.add_row("[cyan]Task:[/cyan]", prompt_data["main_prompt"])
    summary.add_row("[cyan]Project Type:[/cyan]", prompt_data["project_type"])
    summary.add_row("[cyan]Language:[/cyan]", prompt_data["language"])
    summary.add_row("[cyan]AI Model:[/cyan]", options["model"])
    summary.add_row("[cyan]Branch:[/cyan]", options["branch"])
    summary.add_row("[cyan]Mode:[/cyan]", "Preview (Dry Run)" if options["dry_run"] else "Execute & Create PR")
    
    panel = Panel(summary, border_style="bright_yellow", title="Execution Plan")
    console.print(panel)
    
    if not Confirm.ask("\n[bold green]Shall we proceed?[/bold green]", default=True):
        console.print("[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(0)

def run_interactive_cli():
    """Main interactive CLI function"""
    try:
        # Clear screen and display art
        os.system('clear' if os.name == 'posix' else 'cls')
        display_ascii_art()
        display_welcome_message()
        
        # Get inputs from user
        repo_url = get_repository_url()
        prompt_data = get_coding_prompt()
        options = get_execution_options(prompt_data)
        
        # Display summary
        display_execution_summary(repo_url, prompt_data, options)
        
        # Import and run the main CLI
        console.print("\n[bold green]Initializing SHIMU CODE...[/bold green]\n")
        
        # Prepare arguments for the main CLI
        cli_args = [
            "--repo-url", repo_url,
            "--prompt", prompt_data["enhanced_prompt"],
            "--model", options["model"],
            "--branch", options["branch"]
        ]
        
        if options["dry_run"]:
            cli_args.append("--dry-run")
        
        # Import the main CLI function
        from cli import main as cli_main
        
        # Create a mock context for click
        import click
        with click.Context(cli_main) as ctx:
            ctx.params = {
                'repo_url': repo_url,
                'prompt': prompt_data["enhanced_prompt"],
                'model': options["model"],
                'branch': options["branch"],
                'dry_run': options["dry_run"]
            }
            
            # Run the main CLI function
            import asyncio
            from cli import process_repository
            
            # Parse repo info
            repo_parts = repo_url.replace('https://github.com/', '').split('/')
            owner, repo_name = repo_parts[0], repo_parts[1]
            
            # Run the process
            asyncio.run(process_repository(
                repo_url=repo_url,
                owner=owner,
                repo_name=repo_name,
                prompt=prompt_data["enhanced_prompt"],
                model=options["model"],
                branch=options["branch"],
                dry_run=options["dry_run"]
            ))
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Thanks for using SHIMU CODE! See you next time![/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]❌ An error occurred: {str(e)}[/red]")
        console.print("[dim]Please check your configuration and try again.[/dim]")
        sys.exit(1)

@click.command()
def chat():
    """Launch SHIMU CODE interactive chat interface"""
    run_interactive_cli()

if __name__ == "__main__":
    run_interactive_cli()
