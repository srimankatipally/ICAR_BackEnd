# Stage 1: Dependencies (cached layer)
FROM python:3.12-slim AS base

WORKDIR /app

# Install dependencies first (this layer is cached if requirements.txt unchanged)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Application
FROM base AS app

WORKDIR /app

# Copy application code (this layer rebuilds on code changes)
COPY . .

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
