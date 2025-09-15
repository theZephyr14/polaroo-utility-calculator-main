FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY src/ ./src/
COPY render.yaml .
COPY setup_supabase.py .
COPY supabase_schema.sql .

# Set environment variables
ENV PYTHONPATH=/app/src

# Expose port
EXPOSE 8000

# Start command
CMD ["uvicorn", "src.api_supabase:app", "--host", "0.0.0.0", "--port", "8000"]
