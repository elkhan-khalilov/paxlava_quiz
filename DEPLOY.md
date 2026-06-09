# Paxlava Quiz — Deploy təlimatı (quiz.dcl.az)

Bu tətbiq Docker konteyneri kimi qablaşdırılıb və mövcud **nginx-proxy**
konteynerinizin arxasında `quiz.dcl.az` ünvanında işləyəcək.

```
İnternet ──▶ nginx-proxy (80/443) ──▶ paxlava-quiz:8000 (gunicorn)
                                            └── /data (kalıcı volume: games.json, teams_list.json)
```

## 1. DNS

`dcl.az` DNS panelində `quiz` üçün **A** qeydi əlavə edin və serverinizin
IP ünvanına yönləndirin:

```
quiz.dcl.az.   A   <SERVER_IP>
```

## 2. Kodu serverə gətirin

```bash
git clone <repo-url> paxlava_quiz   # və ya git pull
cd paxlava_quiz
```

## 3. Mühit dəyişənləri (.env)

```bash
cp .env.example .env
# SECRET_KEY yarat:
python3 -c "import secrets; print(secrets.token_hex(32))"
```

`.env` faylını doldurun:

- `SECRET_KEY` — yuxarıdakı təsadüfi açar (boş qoymayın, compass error verəcək).
- `ADMIN_PASSWORD`, `USER_PASSWORD` — **mütləq dəyişin** (default: admin123 / user123).
- `SESSION_COOKIE_SECURE=true` — HTTPS olduğu üçün belə qalsın.
- `PROXY_NETWORK` — nginx-proxy-nin qoşulu olduğu şəbəkə (aşağıya bax).

### nginx-proxy şəbəkəsini tapın

```bash
docker inspect nginx-proxy -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}'
```

Çıxan adı `.env` faylındakı `PROXY_NETWORK`-ə yazın. Əgər nginx-proxy yalnız
`bridge` şəbəkəsindədirsə, ayrıca user-defined şəbəkə yaradıb hər ikisini ora
qoşmaq lazımdır:

```bash
docker network create webproxy
docker network connect webproxy nginx-proxy
# .env -> PROXY_NETWORK=webproxy
```

## 4. Konteyneri qaldırın

```bash
docker compose up -d --build
docker compose logs -f paxlava      # log-lara baxış
```

Yoxlama (konteyner host-a port açmır, ona görə nginx şəbəkəsindən sınayın):

```bash
docker exec nginx-proxy wget -qO- http://paxlava-quiz:8000/ | head
```

## 5. nginx-proxy konfiqurasiyası

`deploy/nginx/quiz.dcl.az.conf` faylını nginx-proxy-nin conf qovluğuna əlavə
edin (mövcud dcl.az konfiqinizlə eyni yerə, adətən `/etc/nginx/conf.d/`).

**SSL sertifikatı** (əgər `*.dcl.az` wildcard sertifikatınız yoxdursa):

```bash
# nginx-proxy quraşdırmanıza uyğun certbot üsulu ilə:
certbot certonly --webroot -w /var/www/certbot -d quiz.dcl.az
```

Konfiqdəki `ssl_certificate` yollarını mövcud quraşdırmanızla uyğunlaşdırın,
sonra:

```bash
docker exec nginx-proxy nginx -t
docker exec nginx-proxy nginx -s reload
```

Artıq **https://quiz.dcl.az** işləməlidir.

## 6. Yeniləmə

```bash
git pull
docker compose up -d --build
```

Məlumat (`games.json`, `teams_list.json`) `paxlava-data` volume-ində qalır,
yenidən qurulanda itmir.

```bash
docker run --rm -v paxlava-data:/data alpine cat /data/games.json   # yedək/baxış
```

## Qeydlər / sonrakı təkmilləşmələr

- Giriş istifadəçiləri kodda sabitdir (`admin`, `user`); parollar `.env`-dən gəlir.
  Çoxlu istifadəçi lazım olsa, verilənlər bazasına keçid tövsiyə olunur.
- Məlumat JSON fayllarda saxlanılır — eyni anda çox yazma üçün nəzərdə tutulmayıb;
  bir quiz idarəçisi üçün kifayətdir.
- Köhnə `homepage.html` və `teams.json` faylları tətbiqdə istifadə olunmur
  (image-ə də daxil edilmir).
