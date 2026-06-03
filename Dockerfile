# Paxlava Quiz — production image
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data

WORKDIR /app

# Asılılıqları əvvəlcə qur (layer cache üçün)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tətbiq faylları
COPY main.py .
COPY static/ ./static/

# Kalıcı məlumat qovluğu + root olmayan istifadəçi
RUN mkdir -p /data \
 && useradd --create-home --uid 10001 appuser \
 && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8000

# Gunicorn ilə servis et (nginx-proxy arxasında, daxili port 8000)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", \
     "--workers", "2", "--threads", "4", "--timeout", "60", \
     "--access-logfile", "-", "--error-logfile", "-", \
     "main:app"]
