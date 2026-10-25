import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

SCHEMA = '''
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dishes(id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, tags TEXT NOT NULL DEFAULT '[]', ingredients TEXT NOT NULL DEFAULT '[]', note TEXT NOT NULL DEFAULT '', favorite INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, version INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS plans(day TEXT PRIMARY KEY, dish_id INTEGER REFERENCES dishes(id), status TEXT NOT NULL CHECK(status IN ('suggested','confirmed','fixed','empty')), version INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, day TEXT NOT NULL UNIQUE, dish_id INTEGER NOT NULL REFERENCES dishes(id), version INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS rejections(day TEXT NOT NULL,dish_id INTEGER NOT NULL REFERENCES dishes(id),PRIMARY KEY(day,dish_id));
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS attempts(ip TEXT PRIMARY KEY,count INTEGER NOT NULL,until REAL NOT NULL);
CREATE TABLE IF NOT EXISTS shopping(key TEXT PRIMARY KEY,name TEXT NOT NULL,amount REAL,unit TEXT NOT NULL DEFAULT '',done INTEGER NOT NULL DEFAULT 0,manual INTEGER NOT NULL DEFAULT 0,version INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS migrations(version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO migrations VALUES(1);
INSERT OR IGNORE INTO settings VALUES('revision','0');
'''

def path():
    return os.getenv('DATABASE_PATH', '/data/essen.sqlite3')


def connect():
    os.makedirs(os.path.dirname(os.path.abspath(path())), exist_ok=True)
    c = sqlite3.connect(path(), timeout=15, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA synchronous=FULL')
    return c


def init():
    c = connect()
    try:
        c.executescript(SCHEMA)
        c.execute('BEGIN IMMEDIATE')
        c.execute("INSERT OR IGNORE INTO settings VALUES('modified_at',?)", (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),))
        if not c.execute('SELECT 1 FROM migrations WHERE version=2').fetchone():
            c.execute("ALTER TABLE dishes ADD COLUMN effort TEXT NOT NULL DEFAULT 'normal' CHECK(effort IN ('quick','normal','elaborate'))")
            c.execute('UPDATE dishes SET version=version+1')
            c.execute("UPDATE settings SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")
            c.execute('INSERT INTO migrations VALUES(2)')
        if not c.execute('SELECT 1 FROM migrations WHERE version=3').fetchone():
            c.execute('ALTER TABLE dishes ADD COLUMN frequency_factor REAL NOT NULL DEFAULT 1 CHECK(frequency_factor IN (0.5,0.75,1,1.5,2))')
            c.execute('UPDATE dishes SET version=version+1')
            c.execute("UPDATE settings SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")
            c.execute('INSERT INTO migrations VALUES(3)')
        c.commit()
    except BaseException:
        c.rollback()
        raise
    finally:
        c.close()


@contextmanager
def transaction(write=False):
    c = connect()
    try:
        c.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
        before = c.total_changes
        yield c
        if write and c.total_changes > before:
            c.execute("UPDATE settings SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")
            c.execute("INSERT INTO settings VALUES('modified_at',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),))
        c.commit()
    except BaseException:
        c.rollback()
        raise
    finally:
        c.close()
