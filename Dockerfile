# Lightweight Dockerfile for cineman (Flask + LangChain + external APIs)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal system deps that may be needed (update if you need libs for ML packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency lists then install for Docker cache friendliness
# Use requirements.lock for reproducible builds with hash verification
COPY requirements.txt requirements.lock /app/
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.lock

# Copy app code
COPY . /app

# Expose port (Render provides $PORT at runtime)
EXPOSE 8000

# Use gunicorn with explicit module:variable pointing to your Flask app
# Bind to $PORT (Render sets this), default to 8000 locally
CMD ["sh", "-c", "gunicorn cineman.app:app --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]