"""
models.py
---------
User: one registered account.
Subscription: one subscription record, owned by one User.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    id: Optional[int]
    username: str
    password_hash: str


@dataclass
class Subscription:
    id: Optional[int]
    user_id: int
    service_name: str
    category: str
    cost: float
    billing_cycle: str
    next_renewal_date: str
    status: str = "Active"
    notes: str = ""

    def monthly_cost(self) -> float:
        if self.billing_cycle == "Yearly":
            return self.cost / 12
        return self.cost

    def yearly_cost(self) -> float:
        if self.billing_cycle == "Monthly":
            return self.cost * 12
        return self.cost

    def __str__(self) -> str:
        return f"{self.service_name} ({self.category}) - P{self.cost:.2f}/{self.billing_cycle} - {self.status}"
