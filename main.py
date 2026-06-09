from flask import Flask, request, redirect, url_for, session, render_template_string, flash, get_flashed_messages
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
from html import escape
import os

import db

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

users = {
    "admin": {"password": generate_password_hash("admin123"), "role": "admin"},
    "user": {"password": generate_password_hash("user123"), "role": "user"}
}

# Create the SQLite database (inside DATA_DIR) and import any existing JSON
# data exactly once. The DB file lives in the same volume as the old files.
db.migrate_json_if_needed()

ROUND_FIELDS = [
    ("round_1", "Tur 1"),
    ("round_2", "Tur 2"),
    ("round_3", "Tur 3"),
    ("round_4", "Tur 4"),
    ("round_5", "Tur 5"),
    ("round_6", "Tur 6"),
    ("round_7", "Tur 7"),
    ("round_8", "Tur 8"),
    ("round_8_1", "Tur 8(1)"),
    ("round_8_2", "Tur 8(2)"),
    ("round_8_3", "Tur 8(3)"),
]


def to_int(value, default=0):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def get_game_by_date(games, game_date):
    return next((game for game in games if game.get("date") == game_date), None)


def get_round_value(rounds, field):
    legacy_map = {
        "round_8_1": "round_8(1)",
        "round_8_2": "round_8(2)",
        "round_8_3": "round_8(3)",
    }
    if field in rounds:
        return rounds.get(field, 0)
    return rounds.get(legacy_map.get(field, ""), 0)


def normalize_rounds(rounds):
    normalized = {}
    for field, _ in ROUND_FIELDS:
        normalized[field] = int(get_round_value(rounds, field) or 0)
    return normalized


def calculate_total(rounds):
    return sum(int(get_round_value(rounds, field) or 0) for field, _ in ROUND_FIELDS)


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

    .container { width: min(1280px, 94%); margin: 44px auto; }

    .card {
        background: var(--white-glass); border: 1px solid var(--border); border-radius: 26px; padding: 30px;
        box-shadow: var(--shadow); backdrop-filter: blur(12px);
    }

    h1, h2, h3 { color: var(--blue-700); }
    h1 { font-size: 48px; margin-bottom: 16px; }
    h2 { font-size: 30px; margin-bottom: 18px; }
    h3 { font-size: 22px; margin-bottom: 12px; }
    p { color: var(--muted); line-height: 1.6; }

    .btn {
        display: inline-block; padding: 12px 18px; border-radius: 14px; border: none;
        background: linear-gradient(135deg, var(--blue-500), var(--blue-600)); color: white;
        text-decoration: none; font-weight: 900; cursor: pointer; margin-top: 14px;
        box-shadow: 0 14px 28px rgba(30,136,229,0.18); transition: 0.25s;
        white-space: nowrap;
    }

    .btn:hover { background: linear-gradient(135deg, var(--blue-600), var(--blue-700)); transform: translateY(-2px); }
    .btn-secondary { background: var(--blue-100); color: var(--blue-700); box-shadow: none; border: 1px solid var(--border); }
    .btn-danger { background: linear-gradient(135deg, #ef5350, #e53935); }

    form label { display: block; margin: 14px 0 8px; font-weight: 900; color: var(--blue-700); }

    input, select {
        width: 100%; padding: 12px 14px; border-radius: 14px; border: 1px solid var(--border);
        font-size: 15px; outline: none; background: rgba(255,255,255,0.9); color: var(--text);
    }

    input:focus, select:focus { border-color: var(--blue-500); box-shadow: 0 0 0 4px rgba(66,165,245,0.18); }

    table {
        width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 18px; overflow: hidden;
        border-radius: 18px; border: 1px solid var(--border); box-shadow: 0 18px 36px rgba(30,136,229,0.08);
    }

    th, td { padding: 10px; text-align: left; border-bottom: 1px solid rgba(66,165,245,0.14); }
    th { background: linear-gradient(135deg, var(--blue-500), var(--blue-600)); color: white; font-size: 14px; }
    td { background: rgba(255,255,255,0.76); color: var(--text); font-weight: 700; }
    tr:last-child td { border-bottom: none; }

    .grid { display: grid; grid-template-columns: 360px 1fr; gap: 24px; align-items: start; }
    .message { padding: 12px 16px; border-radius: 14px; margin-bottom: 18px; background: var(--blue-100); color: var(--blue-700); font-weight: 800; border: 1px solid var(--border); }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }

    .small-btn {
        padding: 8px 10px; border-radius: 10px; color: white; background: linear-gradient(135deg, var(--blue-500), var(--blue-600));
        text-decoration: none; font-size: 13px; border: none; cursor: pointer; font-weight: 800;
    }

    .small-btn.secondary { background: linear-gradient(135deg, var(--blue-400), var(--blue-500)); }
    .small-btn.danger { background: linear-gradient(135deg, #ef5350, #e53935); }

    .round-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
    .table-wrap { overflow-x: auto; }
    .total-cell { color: var(--blue-700); font-size: 18px; font-weight: 900; }
    .score-input { min-width: 78px; padding: 9px 8px; text-align: center; border-radius: 10px; }
    .team-manage-table input { min-width: 180px; }
    .toolbar { display: flex; gap: 12px; flex-wrap: wrap; align-items: end; margin: 18px 0; }
    .toolbar form { display: flex; gap: 10px; align-items: end; flex-wrap: wrap; }
    .toolbar label { margin-top: 0; }
    .inline-form { display: inline; margin: 0; }

    @media (max-width: 980px) {
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
                    <div class="feature-box"><h4>Excel tipli cədvəl</h4><p>Admin xalları birbaşa cədvəldə dəyişə bilir.</p></div>
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
        <div class="info-card"><h3>Avtomatik Toplam</h3><p>Bütün turların xalı avtomatik toplanır və nəticə göstərilir.</p></div>
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
    games = db.load_games()
    selected_date = request.args.get("game_date", "").strip()

    if selected_date:
        selected_game = get_game_by_date(games, selected_date)
        results = []

        if selected_game:
            for item in selected_game.get("results", []):
                results.append({
                    "team_name": item.get("team_name"),
                    "rounds": normalize_rounds(item.get("rounds", {}))
                })

        filter_text = "Seçilmiş tarix üzrə komandaların nəticələri göstərilir."
    else:
        # Tarix seçilməyəndə hər komanda üzrə bütün tarixlərdəki xallar toplanır.
        totals_by_team = {}

        for game in games:
            for item in game.get("results", []):
                team_id = item.get("team_id")
                team_name = item.get("team_name")
                key = team_id if team_id is not None else team_name

                if key not in totals_by_team:
                    totals_by_team[key] = {
                        "team_name": team_name,
                        "rounds": {field: 0 for field, _ in ROUND_FIELDS}
                    }

                for field, _ in ROUND_FIELDS:
                    totals_by_team[key]["rounds"][field] += int(get_round_value(item.get("rounds", {}), field) or 0)

        results = list(totals_by_team.values())
        filter_text = "Tarix seçilməyib: hər komanda üzrə bütün tarixlərin ümumi nəticəsi göstərilir."

    sorted_results = sorted(results, key=lambda item: calculate_total(item.get("rounds", {})), reverse=True)

    rows = "".join([
        f"""
        <tr>
            <td>{index}</td>
            <td>{item['team_name']}</td>
            <td>{get_round_value(item['rounds'], 'round_1')}</td>
            <td>{get_round_value(item['rounds'], 'round_2')}</td>
            <td>{get_round_value(item['rounds'], 'round_3')}</td>
            <td>{get_round_value(item['rounds'], 'round_4')}</td>
            <td>{get_round_value(item['rounds'], 'round_5')}</td>
            <td>{get_round_value(item['rounds'], 'round_6')}</td>
            <td>{get_round_value(item['rounds'], 'round_7')}</td>
            <td>{get_round_value(item['rounds'], 'round_8')}</td>
            <td>{get_round_value(item['rounds'], 'round_8_1')}</td>
            <td>{get_round_value(item['rounds'], 'round_8_2')}</td>
            <td>{get_round_value(item['rounds'], 'round_8_3')}</td>
            <td class="total-cell">{calculate_total(item.get('rounds', {}))}</td>
        </tr>
        """
        for index, item in enumerate(sorted_results, start=1)
    ])

    if not rows:
        rows = '<tr><td colspan="14">Hələ nəticə əlavə edilməyib.</td></tr>'

    content = f"""
    <main class="container">
        <div class="card">
            <h2>Komanda balları</h2>
            <p>{filter_text}</p>

            <form method="GET" action="/scores" style="margin-top: 20px; max-width: 420px;">
                <label>Tarix filteri</label>
                <input type="date" name="game_date" value="{selected_date}">
                <button class="btn" type="submit">Filterlə</button>
                <a class="btn btn-secondary" href="/scores">Ümumi nəticə</a>
            </form>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>#</th><th>Komanda</th><th>Tur 1</th><th>Tur 2</th><th>Tur 3</th><th>Tur 4</th>
                            <th>Tur 5</th><th>Tur 6</th><th>Tur 7</th><th>Tur 8</th><th>Tur 8(1)</th><th>Tur 8(2)</th><th>Tur 8(3)</th><th>Toplam</th>
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

    teams_list = db.load_teams_list()
    games = db.load_games()
    selected_date = request.args.get("game_date") or date.today().isoformat()
    selected_game = get_game_by_date(games, selected_date)
    results = selected_game.get("results", []) if selected_game else []

    # Komandaları sıralı göstərmək üçün xəritə
    results_by_team_id = {item["team_id"]: item for item in results}

    # Həmin tarix üçün xal yazılmış, amma teams_list-dən silinmiş köhnə komandalar da itmesin
    extra_results = [item for item in results if item.get("team_id") not in {team["id"] for team in teams_list}]

    team_rows = "".join([
        f"""
        <tr>
            <td>
                <input type="text" name="team_name_{team['id']}" value="{team['name']}" form="teamManageForm">
            </td>
            <td>
                <div class="actions">
                    <button class="small-btn secondary" type="submit" form="teamManageForm">Yadda saxla</button>
                    <form class="inline-form" method="POST" action="/admin/team-name/{team['id']}/delete" onsubmit="return confirm('Bu komandanı tam silmək istədiyinizə əminsiniz? Bu komandanın bütün tarixlər üzrə nəticələri də silinəcək.')">
                        <button class="small-btn danger" type="submit">Komandanı sil</button>
                    </form>
                </div>
            </td>
        </tr>
        """
        for team in teams_list
    ])

    if not team_rows:
        team_rows = '<tr><td colspan="2">Hələ komanda əlavə edilməyib.</td></tr>'

    score_rows = ""
    row_index = 1

    for team in teams_list:
        result = results_by_team_id.get(team["id"])
        result_id = result["id"] if result else ""
        rounds = normalize_rounds(result.get("rounds", {})) if result else {field: 0 for field, _ in ROUND_FIELDS}

        hidden_inputs = f"""
            <input type="hidden" name="team_id_{row_index}" value="{team['id']}">
            <input type="hidden" name="team_name_{row_index}" value="{team['name']}">
            <input type="hidden" name="result_id_{row_index}" value="{result_id}">
        """

        round_inputs = "".join([
            f'<td><input class="score-input" type="number" name="{field}_{row_index}" value="{rounds.get(field, 0)}" data-row="{row_index}" oninput="updateRowTotal({row_index})"></td>'
            for field, _ in ROUND_FIELDS
        ])

        score_rows += f"""
        <tr>
            <td>{team['name']}{hidden_inputs}</td>
            {round_inputs}
            <td class="total-cell" id="total_{row_index}">{calculate_total(rounds)}</td>
            <td>
                <button class="small-btn danger" type="submit" formaction="/admin/date/{selected_date}/result/{result_id}/delete" formmethod="POST" {'disabled' if not result_id else ''} onclick="return confirm('Bu tarix üzrə sətiri silmək istədiyinizə əminsiniz?')">Sətiri sil</button>
            </td>
        </tr>
        """
        row_index += 1

    # Əgər hansısa nəticə əvvəlki komanda siyahısından qalıbsa, ayrıca göstəririk
    for item in extra_results:
        rounds = normalize_rounds(item.get("rounds", {}))
        hidden_inputs = f"""
            <input type="hidden" name="team_id_{row_index}" value="{item['team_id']}">
            <input type="hidden" name="team_name_{row_index}" value="{item['team_name']}">
            <input type="hidden" name="result_id_{row_index}" value="{item['id']}">
        """
        round_inputs = "".join([
            f'<td><input class="score-input" type="number" name="{field}_{row_index}" value="{rounds.get(field, 0)}" data-row="{row_index}" oninput="updateRowTotal({row_index})"></td>'
            for field, _ in ROUND_FIELDS
        ])

        score_rows += f"""
        <tr>
            <td>{item['team_name']}{hidden_inputs}</td>
            {round_inputs}
            <td class="total-cell" id="total_{row_index}">{calculate_total(rounds)}</td>
            <td>
                <button class="small-btn danger" type="submit" formaction="/admin/date/{selected_date}/result/{item['id']}/delete" formmethod="POST" onclick="return confirm('Bu tarix üzrə sətiri silmək istədiyinizə əminsiniz?')">Sətiri sil</button>
            </td>
        </tr>
        """
        row_index += 1

    if not score_rows:
        score_rows = '<tr><td colspan="15">Hələ komanda əlavə edilməyib.</td></tr>'

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

                <h2>Komandalar</h2>
                <form id="teamManageForm" method="POST" action="/admin/team-names/update"></form>
                <div class="table-wrap">
                    <table class="team-manage-table">
                        <thead>
                            <tr><th>Komanda adı</th><th>Əməliyyat</th></tr>
                        </thead>
                        <tbody>{team_rows}</tbody>
                    </table>
                </div>
            </div>

            <div class="card">
                <h2>Excel tipli xal cədvəli</h2>
                <p>Tarix seçin, xalları birbaşa cədvəldə dəyişin və yadda saxlayın.</p>

                <div class="toolbar">
                    <form method="GET" action="/admin">
                        <div>
                            <label>Tarix filteri</label>
                            <input type="date" name="game_date" value="{selected_date}">
                        </div>
                        <button class="btn" type="submit">Tarixi aç</button>
                    </form>

                    <form method="POST" action="/admin/date/{selected_date}/clear" onsubmit="return confirm('Bu tarix üzrə bütün nəticələri silmək istədiyinizə əminsiniz?')">
                        <button class="btn btn-danger" type="submit">Bu tarixin bütün nəticələrini sil</button>
                    </form>
                </div>

                <form id="scoreTableForm" method="POST" action="/admin/scores/update">
                    <input type="hidden" name="game_date" value="{selected_date}">
                    <input type="hidden" name="row_count" value="{row_index - 1}">

                    <div class="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>Komanda</th>
                                    {''.join([f'<th>{label}</th>' for _, label in ROUND_FIELDS])}
                                    <th>Toplam</th>
                                    <th>Əməliyyat</th>
                                </tr>
                            </thead>
                            <tbody>{score_rows}</tbody>
                        </table>
                    </div>

                    <button class="btn" type="submit">Cədvəli yadda saxla</button>
                </form>
            </div>
        </div>
    </main>

    <script>
        const roundFields = {json.dumps([field for field, _ in ROUND_FIELDS])};

        function updateRowTotal(rowIndex) {{
            let total = 0;
            for (const field of roundFields) {{
                const input = document.querySelector(`[name="${{field}}_${{rowIndex}}"]`);
                if (input && input.value !== "") {{
                    total += parseInt(input.value || "0", 10);
                }}
            }}
            const totalCell = document.getElementById(`total_${{rowIndex}}`);
            if (totalCell) {{
                totalCell.textContent = total;
            }}
        }}
    </script>
    """
    return render_template_string(layout(content))


@app.route("/admin/team-name/add", methods=["POST"])
def add_team_name():
    if not login_required():
        return redirect(url_for("login"))
    if not admin_required():
        return redirect(url_for("scores"))

    team_name = request.form.get("team_name", "").strip()
    if team_name:
        db.add_team(team_name)

    return redirect(url_for("admin"))


@app.route("/admin/team-names/update", methods=["POST"])
def update_team_names():
    if not login_required():
        return redirect(url_for("login"))
    if not admin_required():
        return redirect(url_for("scores"))

    game_date = request.form.get("game_date") or date.today().isoformat()
    team_id = request.form.get("team_id", type=int)
    team = db.get_team(team_id)

    id_to_new_name = {}
    for team in teams:
        new_name = request.form.get(f"team_name_{team['id']}", "").strip()
        if new_name:
            id_to_new_name[team["id"]] = new_name
            team["name"] = new_name

    # Boş buraxılan tur əvvəlki dəyəri saxlayır.
    # Yazılan dəyər isə mənfi olsa belə qəbul edilir.
    provided = {}
    for field_name, _ in ROUND_FIELDS:
        raw_value = request.form.get(field_name, "").strip()
        if raw_value != "":
            provided[field_name] = to_int(raw_value)

    db.upsert_result(game_date, team_id, team["name"], provided)
    return redirect(url_for("admin", game_date=game_date))


@app.route("/admin/scores/update", methods=["POST"])
def update_scores_table():
    if not login_required():
        return redirect(url_for("login"))
    if not admin_required():
        return redirect(url_for("scores"))

    result = db.get_result(result_id)
    if not result:
        return redirect(url_for("admin", game_date=game_date))

    if request.method == "POST":
        rounds = {field_name: to_int(request.form.get(field_name, 0)) for field_name, _ in ROUND_FIELDS}
        db.update_result_rounds(result_id, rounds)
        return redirect(url_for("admin", game_date=game_date))

    # Yalnız bu tarixin cədvəlində göstərilən komandalar saxlanır.
    # Komanda siyahısı ayrıca qalır.
    game["results"] = updated_results

    save_games(games)
    return redirect(url_for("admin", game_date=game_date))


@app.route("/admin/date/<game_date>/result/<int:result_id>/delete", methods=["POST"])
def delete_result(game_date, result_id):
    if not login_required():
        return redirect(url_for("login"))
    if not admin_required():
        return redirect(url_for("scores"))

    db.delete_result(result_id)
    return redirect(url_for("admin", game_date=game_date))


@app.route("/admin/date/<game_date>/clear", methods=["POST"])
def clear_date_results(game_date):
    if not login_required():
        return redirect(url_for("login"))
    if not admin_required():
        return redirect(url_for("scores"))

    games = load_games()
    game = get_game_by_date(games, game_date)

    if game:
        game["results"] = []
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
