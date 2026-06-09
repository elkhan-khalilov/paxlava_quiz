"""One-off migration of the old JSON data into SQLite.

Usually unnecessary — the app migrates automatically on first start. Run it
manually if you want to import JSON explicitly:

    python migrate.py
"""

import db

if __name__ == "__main__":
    summary = db.migrate_json()
    print("Migration finished:")
    print(f"  teams imported : {summary['teams']}")
    print(f"  games imported : {summary['games']}")
    print(f"  results imported: {summary['results']}")
    print(f"  legacy games skipped: {summary['skipped_games']}")
    print(f"  database: {db.DB_PATH}")
