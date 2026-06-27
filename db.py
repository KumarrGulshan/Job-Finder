import sqlite3
import os
from datetime import datetime

DB_PATH = "data/applications.db"

# ─── Init ─────────────────────────────────────────────
def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            url         TEXT    UNIQUE,
            title       TEXT,
            company     TEXT,
            platform    TEXT,
            score       INTEGER DEFAULT 0,
            status      TEXT    DEFAULT 'applied',
            applied_at  TEXT    DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()

# ─── Check duplicate ──────────────────────────────────
def already_applied(url: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT 1 FROM applications WHERE url = ?", (url,)
    ).fetchone()
    conn.close()
    return row is not None

# ─── Log a new application ────────────────────────────
def log_application(url: str, title: str, company: str,
                    platform: str, score: int = 0, status: str = "applied"):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT INTO applications (url, title, company, platform, score, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (url, title, company, platform, score, status))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # already in DB (url is UNIQUE)
    finally:
        conn.close()

# ─── Stats summary ────────────────────────────────────
def get_stats() -> dict:
    conn = sqlite3.connect(DB_PATH)

    total = conn.execute(
        "SELECT COUNT(*) FROM applications"
    ).fetchone()[0]

    by_platform = conn.execute("""
        SELECT platform, COUNT(*) as cnt
        FROM applications
        GROUP BY platform
        ORDER BY cnt DESC
    """).fetchall()

    recent = conn.execute("""
        SELECT title, company, platform, score, status, applied_at
        FROM applications
        ORDER BY applied_at DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    return {
        "total":       total,
        "by_platform": by_platform,
        "recent":      recent,
    }

# ─── Print a nice summary table ───────────────────────
def print_stats():
    stats = get_stats()
    print("\n" + "═" * 52)
    print(f"  📊 Total applications logged : {stats['total']}")
    print("─" * 52)
    for platform, count in stats["by_platform"]:
        print(f"  {platform:<20} {count} jobs")
    print("─" * 52)
    print("  Recent 10 applications:")
    print(f"  {'Title':<28} {'Platform':<10} {'Score'}")
    print("  " + "-" * 48)
    for row in stats["recent"]:
        title, company, platform, score, status, applied_at = row
        title_short = (title[:25] + "...") if len(title) > 25 else title
        print(f"  {title_short:<28} {platform:<10} {score}%")
    print("═" * 52 + "\n")


# ─── Test ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("✅ Database initialized at data/applications.db")

    # Insert a test row
    log_application(
        url      = "https://naukri.com/job/test-123",
        title    = "Java Developer",
        company  = "Test Company",
        platform = "Naukri",
        score    = 85,
        status   = "applied"
    )
    log_application(
        url      = "https://linkedin.com/jobs/view/test-456",
        title    = "Flutter Developer",
        company  = "Demo Corp",
        platform = "LinkedIn",
        score    = 78,
        status   = "applied"
    )

    print("✅ Two test rows inserted")
    print_stats()

    # Test duplicate check
    result = already_applied("https://naukri.com/job/test-123")
    print(f"Duplicate check (should be True): {result}")
