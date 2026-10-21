"""
database.py
------------
Handles the raw SQLite connection and creates the users and
subscriptions tables the first time the app runs.
"""

import os
import sqlite3

DB_FILENAME = "subscriptions.db"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_FILENAME)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            username       TEXT NOT NULL UNIQUE,
            password_hash  TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id            INTEGER NOT NULL,
            service_name       TEXT NOT NULL,
            category           TEXT NOT NULL,
            cost               REAL NOT NULL,
            billing_cycle      TEXT NOT NULL,
            next_renewal_date  TEXT NOT NULL,
            status             TEXT NOT NULL DEFAULT 'Active',
            notes              TEXT DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    conn.commit()
    conn.close()
