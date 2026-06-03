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

## Production: subdomain + avtomatik HTTPS (VPS)

Tətbiqi `quiz.dcl.az` kimi subdomain-də Let's Encrypt SSL ilə yayımlamaq üçün
`docker-compose.prod.yml` Caddy reverse proxy-ni qaldırır (sertifikatlar
avtomatik alınır və yenilənir).

**1. DNS** — domen panelində (dcl.az) A record əlavə et:

```
quiz   A   <VPS_PUBLIC_IP>
```

**2. Firewall** — 80 və 443 portlarını aç (SSL üçün lazımdır):

```bash
sudo ufw allow 80,443/tcp
```

**3. `.env` hazırla** (serverdə):

```bash
cp .env.example .env
# DOMAIN=quiz.dcl.az, SECRET_KEY (random), ADMIN_PASSWORD, USER_PASSWORD
```

**4. İşə sal:**

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Bir-iki dəqiqəyə `https://quiz.dcl.az` hazırdır. Loglar: `docker compose -f docker-compose.prod.yml logs -f caddy`.

> Qeyd: SSL sertifikatı yalnız DNS yayıldıqdan **sonra** alınır. `dig quiz.dcl.az +short` serverin IP-sini qaytarmalıdır.

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
