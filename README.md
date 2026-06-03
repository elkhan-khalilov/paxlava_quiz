# Paxlava Quiz

Komandalar arasında keçirilən bilik yarışı üçün xal idarəetmə platforması (Flask).

## Docker ilə işə salma (tövsiyə olunan)

```bash
# 1. Mühit dəyişənlərini hazırla
cp .env.example .env
# .env içində SECRET_KEY və parolları dəyiş

# 2. Qur və işə sal
docker compose up --build -d
```

Tətbiq `http://localhost:5000` ünvanında açılır.

Data (`games.json`, `teams_list.json`) `quiz_data` adlı Docker volume-da saxlanılır
və konteyner yenidən başladıqda itmir.

Dayandırmaq üçün:

```bash
docker compose down          # data qalır
docker compose down -v       # data ilə birlikdə silir
```

### Yalnız Docker (compose olmadan)

```bash
docker build -t paxlava-quiz .
docker run -d -p 5000:5000 \
  -e SECRET_KEY="$(python -c 'import secrets;print(secrets.token_hex(32))')" \
  -v quiz_data:/app/data \
  paxlava-quiz
```

## Lokal işə salma (development)

```bash
pip install -r requirements.txt
python main.py            # http://localhost:5000
```

Production rejimi üçün:

```bash
gunicorn --bind 0.0.0.0:5000 main:app
```

## Mühit dəyişənləri

| Dəyişən | Default | Təyinat |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key-change-me` | Flask sessiya imzalama açarı (**production-da mütləq dəyiş**) |
| `ADMIN_USERNAME` | `admin` | Admin istifadəçi adı |
| `ADMIN_PASSWORD` | `admin123` | Admin parolu |
| `USER_USERNAME` | `user` | Adi istifadəçi adı |
| `USER_PASSWORD` | `user123` | Adi istifadəçi parolu |
| `DATA_DIR` | tətbiq qovluğu | JSON data fayllarının yeri |
| `PORT` | `5000` | `python main.py` üçün port |
| `FLASK_DEBUG` | (bağlı) | `1` olduqda debug rejimi (yalnız development) |

## Səhifələr

- `/` — Ana səhifə
- `/scores` — Komanda balları (hamıya açıq)
- `/about` — Haqqımızda
- `/login` — Giriş
- `/admin` — Admin paneli (yalnız admin rolu)
