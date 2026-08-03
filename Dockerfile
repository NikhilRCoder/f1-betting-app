# PitWall — F1 Betting Analytics Platform
# Production container image.
#
#   docker build -t pitwall .
#   docker run -p 8501:8501 -v pitwall_data:/app/data pitwall
#
# The named volume persists the SQLite database, exports and reports across
# container restarts.
FROM python:3.11-slim

# System libraries: libgomp1 is required by XGBoost's OpenMP runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so the layer caches across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application.
COPY . .

# Runtime data directories (also created at start-up by config.settings).
RUN mkdir -p data exports reports logs

EXPOSE 8501

# Container health is the Streamlit core health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
            "--server.port=8501", "--server.address=0.0.0.0"]
