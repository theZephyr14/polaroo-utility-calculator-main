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

# Install Playwright system dependencies manually (skip font packages that don't exist)
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libgobject-2.0-0 \
    libnspr4 \
    libnss3 \
    libnssutil3 \
    libsmime3 \
    libgio-2.0-0 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libexpat1 \
    libxcb1 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libcairo2 \
    libpango-1.0-0 \
    libasound2 \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-unifont \
    && rm -rf /var/lib/apt/lists/*

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
