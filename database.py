import sqlite3
from flask import g

DATABASE = 'cinema.db'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db(app):
    with app.app_context():
        db = get_db()
        with open('schema.sql', 'r') as f:
            db.executescript(f.read())
        # Only seed if tables are empty
        user_count = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        if user_count == 0:
            with open('seed.sql', 'r') as f:
                db.executescript(f.read())
        db.commit()


def close_db(e=None):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()