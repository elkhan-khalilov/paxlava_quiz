FROM python:3.11-slim

# Predictable, log-friendly Python behaviour inside the container.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000 \
    DATA_DIR=/app/data

WORKDIR /app

# Install dependencies first so this layer is cached across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code.
COPY main.py ./
COPY static/ ./static/

# Seed data lives in /app/data. When a named volume is first mounted here
# Docker copies this seed in; afterwards the volume persists across restarts.
RUN mkdir -p /app/data
COPY games.json teams_list.json /app/data/

# Run as a non-root user for safety.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

VOLUME ["/app/data"]
EXPOSE 5000

# Production WSGI server. Single worker keeps the JSON file store consistent;
# requests are still served concurrently via threads.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "60", "main:app"]
