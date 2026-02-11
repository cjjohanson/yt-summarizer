# Stage 1: Build React frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Final image with Python backend + built frontend
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/src/ ./src/
COPY backend/prompts/ ./prompts/

# Copy pre-built React app from Stage 1
COPY --from=frontend-build /app/frontend/dist ./static/

RUN mkdir -p /app/output /app/data

# Default: run the FastAPI server (serves API + frontend static files)
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
