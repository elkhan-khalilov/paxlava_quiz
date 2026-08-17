#!/bin/sh
# Render (və digər hostlar) diski root sahibliyi ilə mount edir. Konteyner
# birbaşa qeyri-root istifadəçi kimi başlasa, SQLite həmin qovluğa yaza bilmir.
# Ona görə entrypoint root kimi başlayır, qovluğun sahibini düzəldir, sonra
# gunicorn worker-lərini appuser altına endirir.
set -e

DATA_DIR="${DATA_DIR:-/app/data}"
mkdir -p "$DATA_DIR"

# Disk boşdursa, image-dəki seed faylları bir dəfəlik köçürülür.
for seed in games.json teams_list.json; do
    if [ -f "/app/seed/$seed" ] && [ ! -f "$DATA_DIR/$seed" ]; then
        cp "/app/seed/$seed" "$DATA_DIR/$seed"
    fi
done

# root deyiliksə chown alınmayacaq — problem deyil, sadəcə keçirik.
chown -R appuser:appuser "$DATA_DIR" 2>/dev/null || true

exec gunicorn \
    --bind "0.0.0.0:${PORT:-5000}" \
    --workers 1 \
    --threads 4 \
    --timeout 60 \
    --user appuser \
    --group appuser \
    main:app
