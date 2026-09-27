"""
DevPlay Flask — Modelos y base de datos (SQLite + sqlite3 stdlib)
Misma estructura de datos que la versión Next.js/Prisma, pero 100% Python.
"""
import os
import sqlite3
import uuid
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "devplay.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id            TEXT PRIMARY KEY,
  email         TEXT UNIQUE NOT NULL,
  username      TEXT UNIQUE NOT NULL,
  password_hash TEXT,
  full_name     TEXT,
  bio           TEXT,
  avatar        TEXT,
  banner        TEXT,
  location      TEXT,
  profession    TEXT,
  age           INTEGER,
  role          TEXT DEFAULT 'USER',
  tags          TEXT,
  devcoins      INTEGER DEFAULT 100,
  tour_completed INTEGER DEFAULT 0,
  language      TEXT DEFAULT 'es',
  created_at    TEXT DEFAULT (datetime('now')),
  last_seen     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS posts (
  id         TEXT PRIMARY KEY,
  author_id  TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type       TEXT DEFAULT 'POST',
  content    TEXT,
  media_urls TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author_id);
CREATE INDEX IF NOT EXISTS idx_posts_type ON posts(type);

CREATE TABLE IF NOT EXISTS betas (
  id                  TEXT PRIMARY KEY,
  post_id             TEXT UNIQUE NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  title               TEXT NOT NULL,
  description         TEXT NOT NULL,
  download_type       TEXT DEFAULT 'LINK',
  file_url            TEXT,
  file_size           INTEGER,
  file_name           TEXT,
  external_url        TEXT,
  beta_status         TEXT DEFAULT 'open_beta',
  genre               TEXT,
  version             TEXT,
  platforms           TEXT,
  tags                TEXT,
  requirements        TEXT,
  changelog           TEXT,
  install_instructions TEXT,
  cover_image         TEXT,
  screenshots         TEXT,
  external_platform   TEXT,
  downloads           INTEGER DEFAULT 0,
  created_at          TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_betas_post ON betas(post_id);

CREATE TABLE IF NOT EXISTS comments (
  id         TEXT PRIMARY KEY,
  post_id    TEXT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  content    TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id);

CREATE TABLE IF NOT EXISTS likes (
  id         TEXT PRIMARY KEY,
  post_id    TEXT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(post_id, user_id)
);

CREATE TABLE IF NOT EXISTS follows (
  id          TEXT PRIMARY KEY,
  follower_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  followee_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at  TEXT DEFAULT (datetime('now')),
  UNIQUE(follower_id, followee_id)
);

CREATE TABLE IF NOT EXISTS dms (
  id           TEXT PRIMARY KEY,
  sender_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  recipient_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  content      TEXT NOT NULL,
  read_at      TEXT,
  created_at   TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_dms_pair ON dms(sender_id, recipient_id);

CREATE TABLE IF NOT EXISTS chat_messages (
  id         TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  username   TEXT NOT NULL,
  content    TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_chat_time ON chat_messages(created_at);

CREATE TABLE IF NOT EXISTS notifications (
  id         TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  from_user  TEXT NOT NULL,
  type       TEXT NOT NULL,
  message    TEXT NOT NULL,
  entity_id  TEXT,
  read       INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pixel_messages (
  id         TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role       TEXT NOT NULL,
  content    TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now'))
);
"""


def get_db():
    """Conexión nueva por request (Flask la cierra al terminar)."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def new_id():
    return uuid.uuid4().hex[:24]


def now_iso():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def q(sql, params=(), one=False):
    """SELECT helper."""
    conn = get_db()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return (rows[0] if rows else None) if one else rows


def execute(sql, params=()):
    """INSERT/UPDATE/DELETE helper — devuelve lastrowid."""
    conn = get_db()
    cur = conn.execute(sql, params)
    conn.commit()
    last = cur.lastrowid
    conn.close()
    return last
