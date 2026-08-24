FROM python:3.11-slim

WORKDIR /code

# System deps needed to build psycopg2 and other C-extension packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

# Basic container-level healthcheck hitting our /health endpoint
HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=5 CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]



