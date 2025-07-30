# Makefile for Backspace CLI

.PHONY: help install test clean run-server lint format

help:  ## Show this help message
	@echo "Backspace CLI - Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies and setup environment
	python setup.py

test:  ## Run tests and validation
	@echo "🧪 Running tests..."
	@python -c "from agent.ai_agent import AIAgent; print('✅ AI Agent import OK')" || echo "❌ AI Agent import failed"
	@python -c "from utils.github import GitHubManager; print('✅ GitHub import OK')" || echo "❌ GitHub import failed"
	@python -c "from sandbox.sandbox_runner import SandboxRunner; print('✅ Sandbox import OK')" || echo "❌ Sandbox import failed"
	@python -c "from api.sse_client import SSEClient; print('✅ SSE Client import OK')" || echo "❌ SSE Client import failed"
	@echo "✅ All import tests completed"

lint:  ## Run code linting
	@echo "🔍 Running linting..."
	@python -m py_compile cli.py && echo "✅ cli.py syntax OK" || echo "❌ cli.py syntax error"
	@python -m py_compile agent/ai_agent.py && echo "✅ ai_agent.py syntax OK" || echo "❌ ai_agent.py syntax error"
	@python -m py_compile utils/github.py && echo "✅ github.py syntax OK" || echo "❌ github.py syntax error"
	@python -m py_compile sandbox/sandbox_runner.py && echo "✅ sandbox_runner.py syntax OK" || echo "❌ sandbox_runner.py syntax error"

clean:  ## Clean up temporary files and caches
	@echo "🧹 Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.backup" -delete
	rm -rf .pytest_cache/
	rm -rf tmp/
	@echo "✅ Cleanup completed"

run-server:  ## Start the SSE server
	@echo "🚀 Starting SSE server..."
	python -m uvicorn api.server:app --reload --host 0.0.0.0 --port 8000

dev-server:  ## Start server in development mode with hot reload
	@echo "🔥 Starting development server..."
	python -m uvicorn api.server:app --reload --host 127.0.0.1 --port 8000 --log-level debug

example:  ## Show example usage
	@echo "📋 Example usage:"
	@echo "  python cli.py --repo-url https://github.com/user/repo --prompt 'Add a login page'"
	@echo "  python cli.py --repo-url https://github.com/user/repo --prompt 'Fix the bug in auth' --dry-run"
	@echo "  python cli.py --repo-url https://github.com/user/repo --prompt 'Add tests' --model gpt-4"

check-env:  ## Check environment configuration
	@echo "🔧 Checking environment..."
	@python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ GITHUB_TOKEN configured' if os.getenv('GITHUB_TOKEN') and os.getenv('GITHUB_TOKEN') != 'your_personal_access_token_here' else '❌ GITHUB_TOKEN not configured')"
	@python -c "import requests; print('✅ Ollama running' if requests.get('http://localhost:11434').status_code == 200 else '❌ Ollama not running')" 2>/dev/null || echo "❌ Ollama not running"

deps:  ## Install Python dependencies only
	pip install -r requirements.txt

upgrade:  ## Upgrade all dependencies
	pip install --upgrade -r requirements.txt

freeze:  ## Freeze current dependencies
	pip freeze > requirements-frozen.txt
	@echo "📦 Dependencies frozen to requirements-frozen.txt"

ollama-setup:  ## Setup Ollama and pull required models
	@echo "🤖 Setting up Ollama..."
	ollama pull codellama
	@echo "✅ CodeLlama model ready"

docker-build:  ## Build Docker image (if using Docker sandbox)
	@echo "🐳 Building Docker image..."
	docker build -t backspace-cli .

status:  ## Show project status
	@echo "📊 Backspace CLI Status:"
	@echo "  Python: $(shell python --version)"
	@echo "  Git: $(shell git --version)"
	@echo "  Docker: $(shell docker --version 2>/dev/null || echo 'Not installed')"
	@echo "  Ollama: $(shell ollama --version 2>/dev/null || echo 'Not installed')"
	@echo "  Project files: $(shell find . -name '*.py' | wc -l) Python files"
