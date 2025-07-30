#!/usr/bin/env python3
"""
Setup script for Backspace CLI
Installs dependencies and sets up the environment
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return None

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")

def check_git():
    """Check if Git is installed"""
    result = run_command("git --version", "Checking Git installation")
    if result is None:
        print("❌ Git is not installed. Please install Git first.")
        sys.exit(1)

def check_docker():
    """Check if Docker is available (optional)"""
    result = run_command("docker --version", "Checking Docker installation")
    if result is None:
        print("⚠️  Docker not found. Sandbox features will be limited.")
        return False
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    # Update pip first
    run_command(f"{sys.executable} -m pip install --upgrade pip", "Updating pip")
    
    # Install requirements
    requirements_file = Path(__file__).parent / "requirements.txt"
    if requirements_file.exists():
        result = run_command(
            f"{sys.executable} -m pip install -r {requirements_file}", 
            "Installing requirements"
        )
        if result is None:
            print("❌ Failed to install requirements")
            return False
    else:
        print("⚠️  requirements.txt not found, installing core dependencies...")
        core_deps = [
            "fastapi==0.104.1",
            "uvicorn==0.24.0",
            "gitpython==3.1.40",
            "requests==2.31.0",
            "click==8.1.7",
            "rich==13.7.0",
            "python-dotenv==1.0.0",
            "aiofiles==23.2.1",
            "httpx==0.25.2"
        ]
        
        for dep in core_deps:
            result = run_command(f"{sys.executable} -m pip install {dep}", f"Installing {dep}")
            if result is None:
                print(f"⚠️  Failed to install {dep}")
    
    return True

def setup_environment():
    """Set up environment file"""
    env_file = Path(__file__).parent / ".env"
    
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    print("📝 Creating .env file...")
    
    env_content = '''# GitHub Personal Access Token
# Generate one at: https://github.com/settings/tokens
# Required scopes: repo, workflow
GITHUB_TOKEN=your_personal_access_token_here

# Optional: OpenAI API Key (if using cloud-based inference)
OPENAI_API_KEY=your_openai_api_key_here

# Local LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=codellama

# Sandbox Configuration
SANDBOX_DIR=/tmp/backspace-sandbox
MAX_REPO_SIZE_MB=100
'''
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        print("✅ Created .env file")
        print("⚠️  Please edit .env file and add your GitHub token")
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")

def check_ollama():
    """Check if Ollama is installed and running"""
    print("🔍 Checking Ollama installation...")
    
    # Check if ollama command exists
    result = run_command("ollama --version", "Checking Ollama version")
    if result is None:
        print("⚠️  Ollama not found. Install from: https://ollama.ai")
        print("   Or set OPENAI_API_KEY in .env to use OpenAI instead")
        return False
    
    # Check if Ollama service is running
    result = run_command("ollama list", "Checking Ollama models")
    if result is None:
        print("⚠️  Ollama service not running. Start with: ollama serve")
        return False
    
    # Check if codellama model is available
    if "codellama" not in result:
        print("📥 CodeLlama model not found. Installing...")
        install_result = run_command("ollama pull codellama", "Installing CodeLlama model")
        if install_result is None:
            print("⚠️  Failed to install CodeLlama. You can install it later with: ollama pull codellama")
            return False
    
    print("✅ Ollama setup complete")
    return True

def create_directories():
    """Create necessary directories"""
    base_dir = Path(__file__).parent
    directories = [
        base_dir / "logs",
        base_dir / "tmp",
        Path.home() / ".backspace-cli"
    ]
    
    for directory in directories:
        try:
            directory.mkdir(exist_ok=True)
            print(f"✅ Created directory: {directory}")
        except Exception as e:
            print(f"⚠️  Failed to create directory {directory}: {e}")

def test_installation():
    """Test if the installation works"""
    print("🧪 Testing installation...")
    
    try:
        # Test imports
        import fastapi
        import uvicorn
        import git
        import requests
        import click
        import rich
        from dotenv import load_dotenv
        import aiofiles
        import httpx
        
        print("✅ All imports successful")
        
        # Test CLI script
        cli_script = Path(__file__).parent / "cli.py"
        if cli_script.exists():
            result = run_command(f"{sys.executable} {cli_script} --help", "Testing CLI script")
            if result:
                print("✅ CLI script working")
            else:
                print("⚠️  CLI script test failed")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🛠️  Backspace CLI Setup")
    print("=" * 40)
    
    # Basic checks
    check_python_version()
    check_git()
    docker_available = check_docker()
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Dependency installation failed")
        sys.exit(1)
    
    # Setup environment
    setup_environment()
    
    # Create directories
    create_directories()
    
    # Check Ollama (optional)
    ollama_available = check_ollama()
    
    # Test installation
    if test_installation():
        print("\\n🎉 Setup completed successfully!")
        print("\\n📋 Next steps:")
        print("1. Edit .env file and add your GitHub token")
        if not ollama_available:
            print("2. Install Ollama (https://ollama.ai) or configure OpenAI API key")
        print("3. Run: python cli.py --help")
        print("\\n Example usage:")
        print("   python cli.py --repo-url https://github.com/user/repo --prompt 'Add a login page'")
    else:
        print("\\n❌ Setup completed with errors. Please check the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
