"""
auth_manager.py
-----------------
AuthManager: the only class that touches the users table. Handles
registration, login, changing a password, and deleting an account.
Passwords are hashed with werkzeug (bundled with Flask) — never
stored as plain text.
"""

from typing import Optional

from werkzeug.security import generate_password_hash, check_password_hash

from database import get_connection
from models import User


class AuthManager:
    def register(self, username: str, password: str):
        username = username.strip()
        if not username:
            return None, "Please enter a username."
        if len(password) < 4:
            return None, "Password must be at least 4 characters."
        if self.get_user_by_username(username) is not None:
            return None, "That username is already taken."

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id, None

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.get_user_by_username(username)
        if user is None:
            return None
        if not check_password_hash(user.password_hash, password):
            return None
        return user

    def change_password(self, user_id: int, current_password: str, new_password: str):
        """Returns (True, None) on success, or (False, error_message) on failure."""
        user = self.get_user_by_id(user_id)
        if user is None:
            return False, "Account not found."
        if not check_password_hash(user.password_hash, current_password):
            return False, "Current password is incorrect."
        if len(new_password) < 4:
            return False, "New password must be at least 4 characters."

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), user_id),
        )
        conn.commit()
        conn.close()
        return True, None

    def delete_account(self, user_id: int) -> None:
        """Permanently deletes this user's account row. Does NOT delete their
        subscriptions — that's SubscriptionManager's responsibility, since
        AuthManager only ever touches the users table."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

    def get_user_by_username(self, username: str) -> Optional[User]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return self._row_to_user(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return self._row_to_user(row) if row else None

    @staticmethod
    def _row_to_user(row) -> User:
        return User(id=row["id"], username=row["username"], password_hash=row["password_hash"])
