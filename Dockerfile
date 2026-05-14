FROM python:3.11-slim

WORKDIR /app

# System dependencies for OpenCV (from mediapipe) and MediaPipe
# libx11-6 + libxext6: required by opencv-contrib-python (pulled in by mediapipe)
# libgl1 + libglib2.0-0: OpenGL and GLib used by both opencv and mediapipe
# libgomp1: OpenMP for parallel processing in mediapipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libx11-6 \
    libxext6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first to avoid resolver issues, then install prod dependencies
COPY requirements-prod.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-prod.txt

# Copy application code
COPY backend/ backend/

# Create logs dir and stub env (real secrets injected via Render env vars at runtime)
RUN mkdir -p logs
COPY .env.example .env

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
