# Multi-stage build for Jira Q Business Connector
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy requirements and source code
COPY pyproject.toml setup.py MANIFEST.in ./
COPY src/ ./src/
COPY README.md LICENSE ./

# Install Python dependencies and build the package
RUN pip install --upgrade pip setuptools wheel && \
    pip install . && \
    pip list

# Production stage
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create working directory and set ownership
WORKDIR /app
RUN chown -R appuser:appuser /app

# Copy the installed package from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import jira_q_connector; print('OK')" || exit 1

# Set entry point to use the CLI
ENTRYPOINT ["jira-q-connector"]

# Default command (can be overridden)
CMD ["sync"]

# Metadata labels
LABEL maintainer="Jira Q Business Connector Team" \
      description="Jira On-Premises Custom Connector for Amazon Q Business" \
      version="1.0.0" \
      org.opencontainers.image.title="Jira Q Business Connector" \
      org.opencontainers.image.description="Sync Jira issues to Amazon Q Business" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="AWS" \
      org.opencontainers.image.licenses="MIT" 