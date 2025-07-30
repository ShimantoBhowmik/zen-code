FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/tmp

# Set environment variables
ENV PYTHONPATH=/app
ENV SANDBOX_DIR=/tmp/backspace-sandbox
ENV PYTHONUNBUFFERED=1

# Expose port for SSE server
EXPOSE 8000

# Create a non-root user
RUN useradd -m -u 1000 backspace && \
    chown -R backspace:backspace /app

USER backspace

# Default command
CMD ["python", "cli.py", "--help"]
