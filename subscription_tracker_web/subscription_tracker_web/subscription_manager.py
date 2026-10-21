"""
subscription_manager.py
------------------------
SubscriptionManager: the only class that talks to the subscriptions
table. Every method takes a user_id, so one account never sees or
modifies another account's subscriptions.
"""

from calendar import monthrange
from datetime import datetime, timedelta
from typing import List, Optional

from database import get_connection
from models import Subscription


class SubscriptionManager:
    # ---------- Create ----------
    def add_subscription(self, sub: Subscription, user_id: int) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO subscriptions
                (user_id, service_name, category, cost, billing_cycle,
                 next_renewal_date, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, sub.service_name, sub.category, sub.cost, sub.billing_cycle,
             sub.next_renewal_date, sub.status, sub.notes),
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id

    # ---------- Read ----------
    def get_all_subscriptions(self, user_id: int, status_filter: Optional[str] = None) -> List[Subscription]:
        conn = get_connection()
        cursor = conn.cursor()
        if status_filter and status_filter != "All":
            cursor.execute(
                "SELECT * FROM subscriptions WHERE user_id = ? AND status = ? ORDER BY next_renewal_date ASC",
                (user_id, status_filter),
            )
        else:
            cursor.execute(
                "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY next_renewal_date ASC",
                (user_id,),
            )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_subscription(row) for row in rows]

    def get_subscription_by_id(self, sub_id: int, user_id: int) -> Optional[Subscription]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions WHERE id = ? AND user_id = ?", (sub_id, user_id))
        row = cursor.fetchone()
        conn.close()
        return self._row_to_subscription(row) if row else None

    # ---------- Update ----------
    def update_subscription(self, sub: Subscription, user_id: int) -> None:
        if sub.id is None:
            raise ValueError("Cannot update a subscription without an id.")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE subscriptions
            SET service_name = ?, category = ?, cost = ?, billing_cycle = ?,
                next_renewal_date = ?, status = ?, notes = ?
            WHERE id = ? AND user_id = ?
            """,
            (sub.service_name, sub.category, sub.cost, sub.billing_cycle,
             sub.next_renewal_date, sub.status, sub.notes, sub.id, user_id),
        )
        conn.commit()
        conn.close()

    def cancel_subscription(self, sub_id: int, user_id: int) -> None:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE subscriptions SET status = ? WHERE id = ? AND user_id = ?",
            ("Cancelled", sub_id, user_id),
        )
        conn.commit()
        conn.close()

    # ---------- Delete ----------
    def delete_subscription(self, sub_id: int, user_id: int) -> None:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscriptions WHERE id = ? AND user_id = ?", (sub_id, user_id))
        conn.commit()
        conn.close()

    def delete_all_for_user(self, user_id: int) -> None:
        """Deletes every subscription belonging to this user. Called when an
        account is deleted — AuthManager only removes the users row, this
        is the method responsible for cleaning up that user's subscriptions."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

    # ---------- Reports / summaries ----------
    def get_upcoming_renewals(self, user_id: int, days_ahead: int = 7) -> List[Subscription]:
        today = datetime.now().date()
        cutoff = today + timedelta(days=days_ahead)
        upcoming = []
        for sub in self.get_all_subscriptions(user_id, status_filter="Active"):
            try:
                renewal_date = datetime.strptime(sub.next_renewal_date, "%Y-%m-%d").date()
            except ValueError:
                continue
            if today <= renewal_date <= cutoff:
                upcoming.append(sub)
        return upcoming

    def get_total_monthly_cost(self, user_id: int) -> float:
        return sum(sub.monthly_cost() for sub in self.get_all_subscriptions(user_id, status_filter="Active"))

    def get_total_yearly_cost(self, user_id: int) -> float:
        return sum(sub.yearly_cost() for sub in self.get_all_subscriptions(user_id, status_filter="Active"))

    def get_renewals_for_month(self, user_id: int, year: int, month: int):
        """Returns {day_of_month: [Subscription, ...]} for the Calendar view.

        Monthly subscriptions recur every month from their next_renewal_date
        onward (same day-of-month). Yearly subscriptions only appear in their
        one renewal month, repeating in that same month in later years.
        """
        by_day = {}
        days_in_target_month = monthrange(year, month)[1]

        for sub in self.get_all_subscriptions(user_id, status_filter="Active"):
            try:
                renewal = datetime.strptime(sub.next_renewal_date, "%Y-%m-%d").date()
            except ValueError:
                continue

            if sub.billing_cycle == "Monthly":
                if (year, month) >= (renewal.year, renewal.month):
                    day = min(renewal.day, days_in_target_month)
                    by_day.setdefault(day, []).append(sub)
            else:  # Yearly
                if renewal.month == month and year >= renewal.year:
                    day = min(renewal.day, days_in_target_month)
                    by_day.setdefault(day, []).append(sub)

        return by_day

    @staticmethod
    def _row_to_subscription(row) -> Subscription:
        return Subscription(
            id=row["id"], user_id=row["user_id"], service_name=row["service_name"],
            category=row["category"], cost=row["cost"], billing_cycle=row["billing_cycle"],
            next_renewal_date=row["next_renewal_date"], status=row["status"], notes=row["notes"] or "",
        )
