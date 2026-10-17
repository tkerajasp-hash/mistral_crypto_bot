# Dockerfile for DCA Trailing Bot
# Multi-stage build to reduce image size

# Build stage
FROM python:3.9-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY bots/dca_trailing_bot/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.9-slim

WORKDIR /app

# Create non-root user for security
RUN useradd -m botuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/botuser/.local

# Make sure scripts in .local are usable
ENV PATH=/home/botuser/.local/bin:$PATH

# Copy application code
COPY bots/dca_trailing_bot/ .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER botuser

# Set working directory
WORKDIR /app

# Default command (can be overridden)
CMD ["python3", "__main__.py"]
