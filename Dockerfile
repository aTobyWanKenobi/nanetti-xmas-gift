# Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
# Copy dependency files
COPY frontend/package.json frontend/package-lock.json ./
# Install dependencies
RUN npm ci
# Copy source
COPY frontend/ ./
# Build (output to dist)
RUN npm run build

# Build Backend
FROM python:3.12-slim
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy backend
COPY backend/ /app/backend/
WORKDIR /app/backend

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist /app/backend/static

# Env vars
ENV PATH="/app/backend/.venv/bin:$PATH"

# Run
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
