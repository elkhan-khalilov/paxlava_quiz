from flask import Flask, request, redirect, url_for, session, render_template_string, flash, get_flashed_messages
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import json
import os

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

users = {
    "admin": {"password": generate_password_hash("admin123"), "role": "admin"},
    "user": {"password": generate_password_hash("user123"), "role": "user"}
}

DATA_FILE = "games.json"
TEAMS_FILE = "teams_list.json"


def ensure_file(path, default_data):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as file:
            json.dump(default_data, file, ensure_ascii=False, indent=4)


def load_json(path, default_data):
    ensure_file(path, default_data)
    with open(path, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return default_data


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def load_games():
    return load_json(DATA_FILE, [])


def save_games(games):
    save_json(DATA_FILE, games)


def load_teams_list():
    return load_json(TEAMS_FILE, [])


def save_teams_list(teams):
    save_json(TEAMS_FILE, teams)


def get_next_id(items):
    return max([item.get("id", 0) for item in items], default=0) + 1


def get_game_by_date(games, game_date):
    return next((game for game in games if game.get("date") == game_date), None)


def calculate_total(rounds):
    return sum(int(rounds.get(f"round_{i}", 0) or 0) for i in range(1, 9))


def login_required():
    return "username" in session


def admin_required():
    return session.get("role") == "admin"


BASE_STYLE = """
<style>
    :root {
        --blue-50: #f3f9ff;
        --blue-100: #e3f2fd;
        --blue-200: #bbdefb;
        --blue-300: #90caf9;
        --blue-400: #64b5f6;
        --blue-500: #42a5f5;
        --blue-600: #1e88e5;
        --blue-700: #1565c0;
        --text: #12324d;
        --muted: #4f6f8f;
        --white-glass: rgba(255,255,255,0.78);
        --border: rgba(66,165,245,0.18);
        --shadow: 0 24px 55px rgba(30,136,229,0.14);
    }

    * { margin: 0; padding: 0; box-sizing: border-box; font-family: Arial, sans-serif; }

    body {
        min-height: 100vh;
        background: linear-gradient(135deg, var(--blue-50), var(--blue-100), var(--blue-200));
        color: var(--text);
    }

    header {
        padding: 18px 8%;
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: rgba(255,255,255,0.72);
        backdrop-filter: blur(14px);
        border-bottom: 1px solid var(--border);
        position: sticky;
        top: 0;
        z-index: 10;
        box-shadow: 0 10px 30px rgba(30,136,229,0.08);
    }

    .logo { display: flex; align-items: center; gap: 14px; font-size: 24px; font-weight: 900; color: var(--blue-700); }

    .logo img {
        width: 58px; height: 58px; object-fit: cover; border-radius: 16px; background: white; padding: 4px;
        box-shadow: 0 10px 24px rgba(21, 101, 192, 0.16);
    }

    nav a {
        margin-left: 22px; color: var(--blue-700); text-decoration: none; font-weight: 800;
        padding: 10px 12px; border-radius: 12px; transition: 0.25s;
    }

    nav a:hover { color: var(--blue-600); background: var(--blue-100); }

    .container { width: min(1200px, 92%); margin: 50px auto; }

    .card {
        background: var(--white-glass); border: 1px solid var(--border); border-radius: 26px; padding: 30px;
        box-shadow: var(--shadow); backdrop-filter: blur(12px);
    }

    h1, h2, h3 { color: var(--blue-700); }
    h1 { font-size: 48px; margin-bottom: 16px; }
    h2 { font-size: 32px; margin-bottom: 20px; }
    p { color: var(--muted); line-height: 1.6; }

    .btn {
        display: inline-block; padding: 13px 22px; border-radius: 14px; border: none;
        background: linear-gradient(135deg, var(--blue-500), var(--blue-600)); color: white;
        text-decoration: none; font-weight: 900; cursor: pointer; margin-top: 18px;
        box-shadow: 0 14px 28px rgba(30,136,229,0.22); transition: 0.25s;
    }

    .btn:hover { background: linear-gradient(135deg, var(--blue-600), var(--blue-700)); transform: translateY(-2px); }
    .btn-secondary { background: var(--blue-100); color: var(--blue-700); box-shadow: none; border: 1px solid var(--border); }

    form label { display: block; margin: 14px 0 8px; font-weight: 900; color: var(--blue-700); }

    input, select {
        width: 100%; padding: 14px 16px; border-radius: 14px; border: 1px solid var(--border);
        font-size: 16px; outline: none; background: rgba(255,255,255,0.9); color: var(--text);
    }

    input:focus, select:focus { border-color: var(--blue-500); box-shadow: 0 0 0 4px rgba(66,165,245,0.18); }

    table {
        width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 24px; overflow: hidden;
        border-radius: 18px; border: 1px solid var(--border); box-shadow: 0 18px 36px rgba(30,136,229,0.08);
    }

    th, td { padding: 13px; text-align: left; border-bottom: 1px solid rgba(66,165,245,0.14); }
    th { background: linear-gradient(135deg, var(--blue-500), var(--blue-600)); color: white; }
    td { background: rgba(255,255,255,0.74); color: var(--text); font-weight: 700; }
    tr:last-child td { border-bottom: none; }

    .grid { display: grid; grid-template-columns: 360px 1fr; gap: 24px; align-items: start; }
    .message { padding: 12px 16px; border-radius: 14px; margin-bottom: 18px; background: var(--blue-100); color: var(--blue-700); font-weight: 800; border: 1px solid var(--border); }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; }

    .small-btn {
        padding: 8px 12px; border-radius: 10px; color: white; background: linear-gradient(135deg, var(--blue-500), var(--blue-600));
        text-decoration: none; font-size: 14px; border: none; cursor: pointer; font-weight: 800;
    }

    .small-btn.secondary { background: linear-gradient(135deg, var(--blue-400), var(--blue-500)); }
    .small-btn.danger { background: linear-gradient(135deg, var(--blue-300), var(--blue-600)); }

    .round-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
    .table-wrap { overflow-x: auto; }
    .total-cell { color: var(--blue-700); font-size: 18px; font-weight: 900; }

    @media (max-width: 900px) {
        header { flex-direction: column; gap: 16px; }
        nav a { margin: 0 8px; }
        .grid { grid-template-columns: 1fr; }
        .round-grid { grid-template-columns: 1fr; }
        h1 { font-size: 38px; }
    }
</style>
"""


def layout(content):
    logged_in = "username" in session
    role = session.get("role")

    nav = """
        <a href="/">Ana səhifə</a>
        <a href="/scores">Ballar</a>
        <a href="/about">Haqqımızda</a>
    """

    if logged_in and role == "admin":
        nav += '<a href="/admin">Admin page</a>'

    if logged_in:
        nav += '<a href="/logout">Çıxış</a>'
    else:
        nav += '<a href="/login">Giriş</a>'

    return f"""
    <!DOCTYPE html>
    <html lang="az">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Paxlava Quiz</title>
        {BASE_STYLE}
    </head>
    <body>
        <header>
            <div class="logo">
                <img src="/static/logo.png" alt="Paxlava Logo">
                <span>Paxlava Quiz</span>
            </div>
            <nav>{nav}</nav>
        </header>
        {content}
    </body>
    </html>
    """


@app.route("/")
def home():
    content = """
    <style>
        .hero-section { width: min(1280px, 92%); margin: 30px auto 0; padding: 40px; border-radius: 40px; background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(223,239,255,0.88)); box-shadow: 0 30px 80px rgba(30,136,229,0.12); overflow: hidden; }
        .hero-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; align-items: center; }
        .hero-badge { display: inline-block; padding: 12px 20px; border-radius: 999px; background: rgba(66,165,245,0.12); color: #1e88e5; font-weight: 800; margin-bottom: 24px; }
        .hero-title { font-size: 92px; line-height: 0.95; font-weight: 900; margin-bottom: 24px; color: #0d47a1; }
        .hero-title span { display: block; background: linear-gradient(135deg, #42a5f5, #1565c0); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero-text { font-size: 24px; line-height: 1.7; color: #4f6f8f; max-width: 620px; margin-bottom: 30px; }
        .hero-buttons { display: flex; gap: 18px; flex-wrap: wrap; margin-bottom: 34px; }
        .hero-btn { padding: 18px 30px; border-radius: 18px; text-decoration: none; font-weight: 900; font-size: 17px; }
        .hero-btn.primary { background: linear-gradient(135deg, #42a5f5, #1565c0); color: white; box-shadow: 0 20px 40px rgba(30,136,229,0.24); }
        .hero-btn.secondary { border: 2px solid rgba(66,165,245,0.25); color: #1565c0; background: rgba(255,255,255,0.72); }
        .hero-features { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
        .feature-box { padding: 18px; border-radius: 22px; background: rgba(255,255,255,0.72); border: 1px solid rgba(66,165,245,0.12); }
        .feature-box h4 { color: #1565c0; margin-bottom: 8px; font-size: 18px; }
        .hero-image { position: relative; display: flex; justify-content: center; align-items: center; }
        .hero-circle { width: 520px; height: 520px; border-radius: 50%; background: radial-gradient(circle, rgba(255,255,255,1) 0%, rgba(223,239,255,0.85) 100%); display: flex; justify-content: center; align-items: center; }
        .hero-circle img { width: 280px; object-fit: contain; filter: drop-shadow(0 20px 40px rgba(21,101,192,0.18)); }
        .floating-box { position: absolute; width: 90px; height: 90px; border-radius: 24px; background: linear-gradient(135deg, #64b5f6, #1e88e5); color: white; display: flex; justify-content: center; align-items: center; font-size: 42px; font-weight: 900; box-shadow: 0 24px 40px rgba(30,136,229,0.24); }
        .floating-box.one { top: 60px; left: 40px; transform: rotate(-12deg); }
        .floating-box.two { bottom: 80px; left: 80px; transform: rotate(14deg); }
        .info-section { width: min(1280px, 92%); margin: 40px auto; display: grid; grid-template-columns: repeat(4, 1fr); gap: 22px; }
        .info-card { padding: 28px; border-radius: 28px; background: rgba(255,255,255,0.84); border: 1px solid rgba(66,165,245,0.12); box-shadow: 0 20px 40px rgba(30,136,229,0.08); }
        .info-card h3 { color: #1565c0; margin-bottom: 14px; font-size: 22px; }
        @media (max-width: 980px) { .hero-grid, .info-section { grid-template-columns: 1fr; } .hero-title { font-size: 62px; } .hero-circle { width: 360px; height: 360px; } .hero-circle img { width: 190px; } .hero-features { grid-template-columns: 1fr; } }
    </style>

    <section class="hero-section">
        <div class="hero-grid">
            <div>
                <div class="hero-badge">BİLİK • ƏYLƏNCƏ • RƏQABƏT</div>
                <div class="hero-title">PAXLAVA<span>QUIZ</span></div>
                <div class="hero-text">Biliklərini sına, komandanı qur və zirvəyə yüksəl. Ən ağıllı komanda sən ol!</div>
                <div class="hero-buttons">
                    <a class="hero-btn primary" href="/login">Oyuna Başla</a>
                    <a class="hero-btn secondary" href="/scores">Liderlər</a>
                </div>
                <div class="hero-features">
                    <div class="feature-box"><h4>Komanda Qur</h4><p>Dostlarınla birlikdə yarış və qalib ol.</p></div>
                    <div class="feature-box"><h4>8 Tur</h4><p>Hər tur üzrə xal yazılır və toplam avtomatik hesablanır.</p></div>
                    <div class="feature-box"><h4>Canlı Reytinq</h4><p>Bütün komandaları tarix üzrə izləyin.</p></div>
                </div>
            </div>
            <div class="hero-image">
                <div class="floating-box one">?</div>
                <div class="floating-box two">★</div>
                <div class="hero-circle"><img src="/static/logo.png" alt="Paxlava Quiz Logo"></div>
            </div>
        </div>
    </section>

    <section class="info-section">
        <div class="info-card"><h3>Bilik Yarışı</h3><p>Müxtəlif kateqoriyalar üzrə hazırlanmış suallarla özünü yoxla.</p></div>
        <div class="info-card"><h3>Komanda Ruhu</h3><p>Dostlarınla komanda qur və birlikdə zirvəyə yüksəl.</p></div>
        <div class="info-card"><h3>Dinamik Sistem</h3><p>Admin paneli ilə xallar canlı olaraq yenilənir.</p></div>
        <div class="info-card"><h3>Avtomatik Toplam</h3><p>8 turun xalı avtomatik toplanır və nəticə göstərilir.</p></div>
    </section>
    """
    return render_template_string(layout(content))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = users.get(username)

        if user and check_password_hash(user["password"], password):
            session["username"] = username
            session["role"] = user["role"]
            if user["role"] == "admin":
                return redirect(url_for("admin"))
            return redirect(url_for("scores"))

        flash("Username və ya parol yanlışdır.")

    messages = "".join([f'<div class="message">{message}</div>' for message in get_flashed_messages()])
    content = f"""
    <main class="container">
        <div class="card" style="max-width: 480px; margin: 0 auto;">
            <h2>Giriş</h2>
            {messages}
            <form method="POST">
                <label>Username</label>
                <input type="text" name="username" placeholder="Username daxil edin" required>
                <label>Parol</label>
                <input type="password" name="password" placeholder="Parol daxil edin" required>
                <button class="btn" type="submit">Daxil ol</button>
            </form>
            <p style="margin-top: 18px;"><b>Demo:</b> admin / admin123 və ya user / user123</p>
        </div>
    </main>
    """
    return render_template_string(layout(content))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/scores")
def scores():
    games = load_games()
    selected_date = request.args.get("game_date", "").strip()

    all_results = []

    if selected_date:
        selected_game = get_game_by_date(games, selected_date)
        if selected_game:
            for item in selected_game.get("results", []):
                all_results.append({
                    "date": selected_game.get("date"),
                    "team_name": item.get("team_name"),
                    "rounds": item.get("rounds", {})
                })
    else:
        for game in games:
            for item in game.get("results", []):
                all_results.append({
                    "date": game.get("date"),
                    "team_name": item.get("team_name"),
                    "rounds": item.get("rounds", {})
                })

    sorted_results = sorted(all_results, key=lambda item: calculate_total(item.get("rounds", {})), reverse=True)

    rows = "".join([
        f"""
        <tr>
            <td>{index}</td>
            <td>{item['date']}</td>
            <td>{item['team_name']}</td>
            <td>{item['rounds'].get('round_1', 0)}</td>
            <td>{item['rounds'].get('round_2', 0)}</td>
            <td>{item['rounds'].get('round_3', 0)}</td>
            <td>{item['rounds'].get('round_4', 0)}</td>
            <td>{item['rounds'].get('round_5', 0)}</td>
            <td>{item['rounds'].get('round_6', 0)}</td>
            <td>{item['rounds'].get('round_7', 0)}</td>
            <td>{item['rounds'].get('round_8', 0)}</td>
            <td class="total-cell">{calculate_total(item.get('rounds', {}))}</td>
        </tr>
        """
        for index, item in enumerate(sorted_results, start=1)
    ])

    if not rows:
        rows = '<tr><td colspan="12">Hələ nəticə əlavə edilməyib.</td></tr>'

    filter_text = "Seçilmiş tarix üzrə nəticələr göstərilir." if selected_date else "Bütün tarixlər üzrə indiyə kimi əlavə edilmiş nəticələr göstərilir."

    content = f"""
    <main class="container">
        <div class="card">
            <h2>Komanda balları</h2>
            <p>{filter_text}</p>

            <form method="GET" action="/scores" style="margin-top: 20px; max-width: 420px;">
                <label>Tarix filteri</label>
                <input type="date" name="game_date" value="{selected_date}">
                <button class="btn" type="submit">Filterlə</button>
                <a class="btn btn-secondary" href="/scores">Bütün nəticələr</a>
            </form>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>#</th><th>Tarix</th><th>Komanda</th><th>Tur 1</th><th>Tur 2</th><th>Tur 3</th><th>Tur 4</th>
                            <th>Tur 5</th><th>Tur 6</th><th>Tur 7</th><th>Tur 8</th><th>Toplam</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        </div>
    </main>
    """
    return render_template_string(layout(content))


@app.route("/admin")
def admin():
    if not login_required():
        return redirect(url_for("login"))
    if not admin_required():
        return redirect(url_for("scores"))

    teams_list = load_teams_list()
    games = load_games()
    selected_date = request.args.get("game_date") or date.today().isoformat()
    selected_game = get_game_by_date(games, selected_date)
    results = selected_game.get("results", []) if selected_game else []

    team_options = "".join([
        f'<option value="{team["id"]}">{team["name"]}</option>'
        for team in teams_list
    ])

    rows = "".join([
        f"""
        <tr>
            <td>{item['team_name']}</td>
            <td>{item['rounds'].get('round_1', 0)}</td>
            <td>{item['rounds'].get('round_2', 0)}</td>
            <td>{item['rounds'].get('round_3', 0)}</td>
            <td>{item['rounds'].get('round_4', 0)}</td>
            <td>{item['rounds'].get('round_5', 0)}</td>
            <td>{item['rounds'].get('round_6', 0)}</td>
            <td>{item['rounds'].get('round_7', 0)}</td>
            <td>{item['rounds'].get('round_8', 0)}</td>
            <td class="total-cell">{calculate_total(item.get('rounds', {}))}</td>
            <td>
                <div class="actions">
                    <a class="small-btn secondary" href="/admin/date/{selected_date}/result/{item['id']}/edit">Editlə</a>
                    <form method="POST" action="/admin/date/{selected_date}/result/{item['id']}/delete" onsubmit="return confirm('Bu nəticəni silmək istədiyinizə əminsiniz?')">
                        <button class="small-btn danger" type="submit">Sil</button>
                    </form>
                </div>
            </td>
        </tr>
        """
        for item in results
    ])

    if not rows:
        rows = '<tr><td colspan="11">Seçilmiş tarix üçün hələ xal əlavə edilməyib.</td></tr>'

    content = f"""
    <main class="container">
        <div class="grid">
            <div class="card">
                <h2>Komanda əlavə et</h2>
                <form method="POST" action="/admin/team-name/add">
                    <label>Komanda adı</label>
                    <input type="text" name="team_name" placeholder="Məsələn: Team A" required>
                    <button class="btn" type="submit">Komandanı yadda saxla</button>
                </form>

                <hr style="margin: 28px 0; border: none; border-top: 1px solid rgba(66,165,245,0.18);">

                <h2>Xal əlavə et</h2>
                <form method="POST" action="/admin/result/add">
                    <label>Tarix seç</label>
                    <input type="date" name="game_date" value="{selected_date}" required>

                    <label>Komanda seç</label>
                    <select name="team_id" required>
                        {team_options if team_options else '<option value="">Əvvəl komanda əlavə edin</option>'}
                    </select>

                    <div class="round-grid">
                        <div><label>Tur 1</label><input type="number" name="round_1" placeholder="0"></div>
                        <div><label>Tur 2</label><input type="number" name="round_2" placeholder="0"></div>
                        <div><label>Tur 3</label><input type="number" name="round_3" placeholder="0"></div>
                        <div><label>Tur 4</label><input type="number" name="round_4" placeholder="0"></div>
                        <div><label>Tur 5</label><input type="number" name="round_5" placeholder="0"></div>
                        <div><label>Tur 6</label><input type="number" name="round_6" placeholder="0"></div>
                        <div><label>Tur 7</label><input type="number" name="round_7" placeholder="0"></div>
                        <div><label>Tur 8</label><input type="number" name="round_8" placeholder="0"></div>
                    </div>

                    <button class="btn" type="submit">Xalları əlavə et</button>
                </form>
            </div>

            <div class="card">
                <h2>Admin page</h2>
                <p>Tarix seçin, həmin tarix üzrə komandaların 8 tur nəticələrini idarə edin.</p>

                <form method="GET" action="/admin" style="margin-top: 20px; max-width: 360px;">
                    <label>Tarix filteri</label>
                    <input type="date" name="game_date" value="{selected_date}" onchange="this.form.submit()">
                </form>

                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Komanda</th><th>Tur 1</th><th>Tur 2</th><th>Tur 3</th><th>Tur 4</th>
                                <th>Tur 5</th><th>Tur 6</th><th>Tur 7</th><th>Tur 8</th><th>Toplam</th><th>Əməliyyat</th>
                            </tr>
                        </thead>
                        <tbody>{rows}</tbody>
                    </table>
                </div>
            </div>
        </div>
    </main>
    """
    return render_template_string(layout(content))


@app.route("/admin/team-name/add", methods=["POST"])
def add_team_name():
    if not login_required():
        return redirect(url_for("login"))
    if not admin_required():
        return redirect(url_for("scores"))

    teams = load_teams_list()
    team_name = request.form.get("team_name", "").strip()

    if team_name and not any(team["name"].lower() == team_name.lower() for team in teams):
        teams.append({"id": get_next_id(teams), "name": team_name})
        save_teams_list(teams)

    return redirect(url_for("admin"))


@app.route("/admin/result/add", methods=["POST"])
def add_result():
    if not login_required():
        return redirect(url_for("login"))
    if not admin_required():
        return redirect(url_for("scores"))

    teams_list = load_teams_list()
    games = load_games()
    game_date = request.form.get("game_date") or date.today().isoformat()
    team_id = request.form.get("team_id", type=int)
    team = next((team for team in teams_list if team["id"] == team_id), None)

    if not team:
        return redirect(url_for("admin", game_date=game_date))

    game = get_game_by_date(games, game_date)
    if not game:
        game = {"id": get_next_id(games), "date": game_date, "results": []}
        games.append(game)

    existing = next((item for item in game.get("results", []) if item["team_id"] == team_id), None)

    if existing:
        rounds = existing.get("rounds", {})
    else:
        rounds = {f"round_{i}": 0 for i in range(1, 9)}

    for i in range(1, 9):
        field_name = f"round_{i}"
        raw_value = request.form.get(field_name, "").strip()

        # Boş buraxılan tur əvvəlki dəyəri saxlayır.
        # Yazılan dəyər isə mənfi olsa belə qəbul edilir.
        if raw_value != "":
            rounds[field_name] = int(raw_value)

    if existing:
        existing["rounds"] = rounds
        existing["team_name"] = team["name"]
    else:
        game.setdefault("results", []).append({
            "id": get_next_id(game.get("results", [])),
            "team_id": team_id,
            "team_name": team["name"],
            "rounds": rounds
        })

    save_games(games)
    return redirect(url_for("admin", game_date=game_date))


@app.route("/admin/date/<game_date>/result/<int:result_id>/edit", methods=["GET", "POST"])
def edit_result(game_date, result_id):
    if not login_required():
        return redirect(url_for("login"))
    if not admin_required():
        return redirect(url_for("scores"))

    games = load_games()
    game = get_game_by_date(games, game_date)
    if not game:
        return redirect(url_for("admin", game_date=game_date))

    result = next((item for item in game.get("results", []) if item["id"] == result_id), None)
    if not result:
        return redirect(url_for("admin", game_date=game_date))

    if request.method == "POST":
        result["rounds"] = {f"round_{i}": int(request.form.get(f"round_{i}", 0) or 0) for i in range(1, 9)}
        save_games(games)
        return redirect(url_for("admin", game_date=game_date))

    rounds = result.get("rounds", {})
    content = f"""
    <main class="container">
        <div class="card" style="max-width: 620px; margin: 0 auto;">
            <h2>Nəticəni editlə</h2>
            <p>Tarix: {game_date} | Komanda: {result['team_name']}</p>
            <form method="POST">
                <div class="round-grid">
                    <div><label>Tur 1</label><input type="number" name="round_1" value="{rounds.get('round_1', 0)}"></div>
                    <div><label>Tur 2</label><input type="number" name="round_2" value="{rounds.get('round_2', 0)}"></div>
                    <div><label>Tur 3</label><input type="number" name="round_3" value="{rounds.get('round_3', 0)}"></div>
                    <div><label>Tur 4</label><input type="number" name="round_4" value="{rounds.get('round_4', 0)}"></div>
                    <div><label>Tur 5</label><input type="number" name="round_5" value="{rounds.get('round_5', 0)}"></div>
                    <div><label>Tur 6</label><input type="number" name="round_6" value="{rounds.get('round_6', 0)}"></div>
                    <div><label>Tur 7</label><input type="number" name="round_7" value="{rounds.get('round_7', 0)}"></div>
                    <div><label>Tur 8</label><input type="number" name="round_8" value="{rounds.get('round_8', 0)}"></div>
                </div>
                <button class="btn" type="submit">Yadda saxla</button>
                <a class="btn btn-secondary" href="/admin?game_date={game_date}">Geri qayıt</a>
            </form>
        </div>
    </main>
    """
    return render_template_string(layout(content))


@app.route("/admin/date/<game_date>/result/<int:result_id>/delete", methods=["POST"])
def delete_result(game_date, result_id):
    if not login_required():
        return redirect(url_for("login"))
    if not admin_required():
        return redirect(url_for("scores"))

    games = load_games()
    game = get_game_by_date(games, game_date)
    if game:
        game["results"] = [item for item in game.get("results", []) if item["id"] != result_id]
        save_games(games)

    return redirect(url_for("admin", game_date=game_date))


@app.route("/about")
def about():
    content = """
    <style>
        .about-wrapper { width: min(1200px, 92%); margin: 40px auto; }
        .about-hero { padding: 50px; border-radius: 38px; background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(227,242,253,0.88)); border: 1px solid rgba(66,165,245,0.16); box-shadow: 0 28px 70px rgba(30,136,229,0.12); text-align: center; margin-bottom: 34px; }
        .about-hero img { width: 140px; height: 140px; object-fit: cover; border-radius: 28px; background: white; padding: 8px; box-shadow: 0 18px 40px rgba(30,136,229,0.18); margin-bottom: 24px; }
        .about-badge { display: inline-block; padding: 10px 18px; border-radius: 999px; background: rgba(66,165,245,0.14); color: #1565c0; font-weight: 900; margin-bottom: 18px; }
        .about-title { font-size: 64px; font-weight: 900; margin-bottom: 20px; color: #1565c0; }
        .about-text { max-width: 860px; margin: 0 auto; font-size: 22px; line-height: 1.8; color: #4f6f8f; }
        .contact-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 22px; }
        .contact-card { padding: 30px; border-radius: 28px; background: rgba(255,255,255,0.82); border: 1px solid rgba(66,165,245,0.16); box-shadow: 0 18px 40px rgba(30,136,229,0.08); text-align: center; transition: 0.25s; }
        .contact-card:hover { transform: translateY(-4px); }
        .contact-icon { width: 78px; height: 78px; margin: 0 auto 18px; border-radius: 24px; background: linear-gradient(135deg, #42a5f5, #1565c0); display: flex; align-items: center; justify-content: center; color: white; font-size: 34px; font-weight: 900; box-shadow: 0 18px 36px rgba(30,136,229,0.18); }
        .contact-card h3 { color: #1565c0; margin-bottom: 12px; font-size: 24px; }
        .contact-card p, .contact-card a { color: #4f6f8f; font-size: 18px; text-decoration: none; word-break: break-word; }
        @media (max-width: 980px) { .contact-grid { grid-template-columns: 1fr; } .about-title { font-size: 44px; } .about-text { font-size: 18px; } }
    </style>

    <section class="about-wrapper">
        <div class="about-hero">
            <img src="/static/logo.png" alt="Paxlava Quiz Logo">
            <div class="about-badge">PAXLAVA QUIZ</div>
            <div class="about-title">Haqqımızda</div>
            <div class="about-text">
                Paxlava Quiz komandalar arasında keçirilən interaktiv bilik yarış platformasıdır.
                Məqsədimiz insanları bir araya gətirmək, əyləncəli və rəqabətli mühit yaratmaq,
                həmçinin bilik və komanda ruhunu inkişaf etdirməkdir.
            </div>
        </div>

        <div class="contact-grid">
            <div class="contact-card"><div class="contact-icon">IG</div><h3>Instagram</h3><p>@paxlava.quiz</p></div>
            <div class="contact-card"><div class="contact-icon">f</div><h3>Facebook</h3><p>Paxlava Quiz</p></div>
            <div class="contact-card"><div class="contact-icon">☎</div><h3>Əlaqə</h3><a href="tel:+994552333470">+994 55 233 34 70</a></div>
            <div class="contact-card"><div class="contact-icon">✉</div><h3>Email</h3><a href="mailto:paxlavaquiz@gmail.com">paxlavaquiz@gmail.com</a></div>
        </div>
    </section>
    """
    return render_template_string(layout(content))


if __name__ == "__main__":
    app.run(debug=True)
