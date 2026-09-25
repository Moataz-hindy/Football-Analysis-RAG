FROM python:3.11-slim

# Prevent Python from writing .pyc and ensure real-time logging output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (gcc and libpq-dev for PostgreSQL, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and files
COPY . .

# Ensure write permissions for outputs and reports (required for Hugging Face UID 1000)
RUN chmod -R 777 /app

# Expose default port
EXPOSE 8000

# Built-in health check satisfying Week 5 Sections 38 & 39
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Launch FastAPI backend with uvicorn (respecting PORT environment variable)
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
