"""SQLite data layer for Paxlava Quiz.

The database file lives inside DATA_DIR (the Docker volume), so it persists
across container/code updates exactly like the old JSON files did. On first
run the existing games.json / teams_list.json are migrated in automatically.
"""

import json
import os
import sqlite3
from contextlib import contextmanager

DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("DB_PATH", os.path.join(DATA_DIR, "quiz.db"))

# Canonical round columns (must match ROUND_FIELDS in main.py).
ROUND_KEYS = [
    "round_1", "round_2", "round_3", "round_4", "round_5",
    "round_6", "round_7", "round_8", "round_8_1", "round_8_2", "round_8_3",
]

# Old JSON used keys like "round_8(1)"; map them to the new column names.
_LEGACY_ROUND_KEYS = {
    "round_8_1": "round_8(1)",
    "round_8_2": "round_8(2)",
    "round_8_3": "round_8(3)",
}


@contextmanager
def get_connection():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    round_cols = ",\n                ".join(f"{key} INTEGER NOT NULL DEFAULT 0" for key in ROUND_KEYS)
    with get_connection() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY,
                date TEXT NOT NULL UNIQUE
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY,
                game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                team_id INTEGER NOT NULL REFERENCES teams(id),
                team_name TEXT NOT NULL,
                {round_cols},
                UNIQUE (game_id, team_id)
            )
        """)


def _to_int(value, default=0):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def _round_value(rounds, key):
    if key in rounds:
        return _to_int(rounds.get(key))
    return _to_int(rounds.get(_LEGACY_ROUND_KEYS.get(key, ""), 0))


def _rounds_from_row(row):
    return {key: row[key] for key in ROUND_KEYS}


# --- Teams -----------------------------------------------------------------

def load_teams_list():
    with get_connection() as conn:
        rows = conn.execute("SELECT id, name FROM teams ORDER BY id").fetchall()
    return [{"id": r["id"], "name": r["name"]} for r in rows]


def get_team(team_id):
    if team_id is None:
        return None
    with get_connection() as conn:
        row = conn.execute("SELECT id, name FROM teams WHERE id = ?", (team_id,)).fetchone()
    return {"id": row["id"], "name": row["name"]} if row else None


def add_team(name):
    name = (name or "").strip()
    if not name:
        return False
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM teams WHERE lower(name) = lower(?)", (name,)).fetchone()
        if exists:
            return False
        conn.execute("INSERT INTO teams (name) VALUES (?)", (name,))
    return True


# --- Games / results -------------------------------------------------------

def load_games():
    """Return the same nested shape the views expect (list of games with
    their results and a rounds dict)."""
    with get_connection() as conn:
        games = conn.execute("SELECT id, date FROM games ORDER BY date").fetchall()
        results = conn.execute("SELECT * FROM results ORDER BY id").fetchall()
    by_game = {}
    for r in results:
        by_game.setdefault(r["game_id"], []).append({
            "id": r["id"],
            "team_id": r["team_id"],
            "team_name": r["team_name"],
            "rounds": _rounds_from_row(r),
        })
    return [
        {"id": g["id"], "date": g["date"], "results": by_game.get(g["id"], [])}
        for g in games
    ]


def get_result(result_id):
    with get_connection() as conn:
        r = conn.execute("SELECT * FROM results WHERE id = ?", (result_id,)).fetchone()
    if not r:
        return None
    return {
        "id": r["id"],
        "team_id": r["team_id"],
        "team_name": r["team_name"],
        "rounds": _rounds_from_row(r),
    }


def _get_or_create_game(conn, game_date):
    row = conn.execute("SELECT id FROM games WHERE date = ?", (game_date,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO games (date) VALUES (?)", (game_date,))
    return cur.lastrowid


def upsert_result(game_date, team_id, team_name, rounds):
    """Create a result for (date, team), or update an existing one. Only the
    round keys present in `rounds` are overwritten; the rest keep their value
    (new rows default missing rounds to 0)."""
    with get_connection() as conn:
        game_id = _get_or_create_game(conn, game_date)
        existing = conn.execute(
            "SELECT id FROM results WHERE game_id = ? AND team_id = ?",
            (game_id, team_id),
        ).fetchone()
        if existing:
            set_clauses = ["team_name = ?"]
            params = [team_name]
            for key, value in rounds.items():
                if key in ROUND_KEYS:
                    set_clauses.append(f"{key} = ?")
                    params.append(_to_int(value))
            params.append(existing["id"])
            conn.execute(f"UPDATE results SET {', '.join(set_clauses)} WHERE id = ?", params)
        else:
            cols = ["game_id", "team_id", "team_name"] + ROUND_KEYS
            values = [game_id, team_id, team_name] + [_to_int(rounds.get(k, 0)) for k in ROUND_KEYS]
            placeholders = ", ".join(["?"] * len(cols))
            conn.execute(f"INSERT INTO results ({', '.join(cols)}) VALUES ({placeholders})", values)


def update_result_rounds(result_id, rounds):
    set_clauses = [f"{k} = ?" for k in ROUND_KEYS]
    params = [_to_int(rounds.get(k, 0)) for k in ROUND_KEYS]
    params.append(result_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE results SET {', '.join(set_clauses)} WHERE id = ?", params)


def delete_result(result_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM results WHERE id = ?", (result_id,))


# --- Migration from the old JSON files -------------------------------------

def _read_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _get_meta(conn, key):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def migrate_json(data_dir=None):
    """Import teams_list.json and games.json into the DB. Idempotent: existing
    rows are not duplicated, and legacy games (old `teams` schema without
    `results`) are skipped."""
    data_dir = data_dir or DATA_DIR
    init_db()
    teams = _read_json(os.path.join(data_dir, "teams_list.json"), [])
    games = _read_json(os.path.join(data_dir, "games.json"), [])
    summary = {"teams": 0, "games": 0, "results": 0, "skipped_games": 0}

    with get_connection() as conn:
        for team in teams:
            name = (team.get("name") or "").strip()
            if not name:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO teams (id, name) VALUES (?, ?)",
                (team.get("id"), name),
            )
            summary["teams"] += 1

        for game in games:
            results = game.get("results")
            if not results:  # legacy `teams` schema — app never displayed these
                summary["skipped_games"] += 1
                continue
            game_date = game.get("date")
            if not game_date:
                summary["skipped_games"] += 1
                continue
            existing_game = conn.execute("SELECT id FROM games WHERE date = ?", (game_date,)).fetchone()
            if existing_game:
                game_id = existing_game["id"]
            else:
                cur = conn.execute("INSERT INTO games (id, date) VALUES (?, ?)", (game.get("id"), game_date))
                game_id = game.get("id") if game.get("id") is not None else cur.lastrowid
            summary["games"] += 1

            for result in results:
                team_id = result.get("team_id")
                team_name = result.get("team_name") or ""
                if team_id is None:
                    continue
                # Guarantee referential integrity for orphaned team references.
                conn.execute(
                    "INSERT OR IGNORE INTO teams (id, name) VALUES (?, ?)",
                    (team_id, team_name or f"Team {team_id}"),
                )
                dup = conn.execute(
                    "SELECT 1 FROM results WHERE game_id = ? AND team_id = ?",
                    (game_id, team_id),
                ).fetchone()
                if dup:
                    continue
                rounds = result.get("rounds", {})
                cols = ["game_id", "team_id", "team_name"] + ROUND_KEYS
                values = [game_id, team_id, team_name] + [_round_value(rounds, k) for k in ROUND_KEYS]
                placeholders = ", ".join(["?"] * len(cols))
                conn.execute(f"INSERT INTO results ({', '.join(cols)}) VALUES ({placeholders})", values)
                summary["results"] += 1

        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('json_migrated', '1')")

    return summary


def migrate_json_if_needed():
    """Run the JSON import exactly once (tracked via the meta table), so it
    never resurrects data that was later deleted through the admin panel."""
    init_db()
    with get_connection() as conn:
        already = _get_meta(conn, "json_migrated")
    if already:
        return None
    return migrate_json()
