# ==============================================================================
# Stage 1: Build React Frontend SPA
# ==============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /build

COPY frontend/package*.json ./
RUN npm ci || npm install

COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Production All-in-One Container (Python FastAPI + Built Frontend)
# ==============================================================================
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ .

# Copy compiled frontend from Stage 1 into backend static_dist
COPY --from=frontend-builder /build/dist ./static_dist

# Persistent volume for SQLite and custom configs
VOLUME ["/data"]

EXPOSE 8000

ENV DATABASE_URL="sqlite:////data/cert_checker.db"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
