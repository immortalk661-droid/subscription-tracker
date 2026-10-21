"""
report_manager.py
-------------------
ReportManager: a dedicated class for the Reports page's calculations.
Kept separate from SubscriptionManager the same way AuthManager is
kept separate — each manager owns exactly one responsibility.
"""

from calendar import month_name
from datetime import datetime
from typing import List, Tuple

from subscription_manager import SubscriptionManager


class ReportManager:
    def __init__(self):
        self.manager = SubscriptionManager()

    def get_category_breakdown(self, user_id: int) -> List[Tuple[str, float]]:
        totals = {}
        for sub in self.manager.get_all_subscriptions(user_id, status_filter="Active"):
            totals[sub.category] = totals.get(sub.category, 0.0) + sub.monthly_cost()
        return sorted(totals.items(), key=lambda item: item[1], reverse=True)

    def get_monthly_projection(self, user_id: int, months_ahead: int = 6) -> List[Tuple[str, float]]:
        subs = self.manager.get_all_subscriptions(user_id, status_filter="Active")
        today = datetime.now().date()

        results = []
        year, month = today.year, today.month
        for _ in range(months_ahead):
            month_total = 0.0
            for sub in subs:
                try:
                    renewal = datetime.strptime(sub.next_renewal_date, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if sub.billing_cycle == "Monthly":
                    if (year, month) >= (renewal.year, renewal.month):
                        month_total += sub.cost
                else:
                    if renewal.month == month and year >= renewal.year:
                        month_total += sub.cost
            results.append((f"{month_name[month][:3]} {year}", month_total))
            month += 1
            if month > 12:
                month = 1
                year += 1
        return results
