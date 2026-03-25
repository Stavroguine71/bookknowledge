FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway sets PORT env var. Use Python to read it for reliability.
CMD python -c "import os; port = os.environ.get('PORT', '8000'); print(f'Starting on port {port}', flush=True); import subprocess; subprocess.run(['uvicorn', 'main:app', '--host', '0.0.0.0', '--port', port])"
