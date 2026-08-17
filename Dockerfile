FROM python:3.11-slim

# NOTE: PORT is deliberately NOT set here — the host (Render) injects it.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/app/data

WORKDIR /app

# Install dependencies first so this layer is cached across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code.
COPY main.py db.py migrate.py ./
COPY static/ ./static/
COPY entrypoint.sh ./
RUN chmod +x /app/entrypoint.sh

# Seed data is kept OUTSIDE the data dir. A mounted disk would otherwise hide
# it; entrypoint.sh copies these across on first boot if the disk is empty.
RUN mkdir -p /app/seed /app/data
COPY games.json teams_list.json /app/seed/

# Non-root user for the actual workers. The container still starts as root so
# entrypoint.sh can fix ownership of a host-mounted disk, then gunicorn drops
# privileges via --user/--group.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

EXPOSE 5000

ENTRYPOINT ["/app/entrypoint.sh"]
