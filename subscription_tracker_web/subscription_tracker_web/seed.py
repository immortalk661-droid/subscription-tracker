"""
seed.py
-------
Creates a demo account and populates it with sample subscriptions.

    username: demo
    password: demo1234
"""

from datetime import date, timedelta

from database import initialize_database, get_connection
from models import Subscription
from subscription_manager import SubscriptionManager
from auth_manager import AuthManager

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo1234"


def clear_existing_data():
    conn = get_connection()
    conn.execute("DELETE FROM subscriptions")
    conn.execute("DELETE FROM users WHERE username = ?", (DEMO_USERNAME,))
    conn.commit()
    conn.close()


def seed():
    initialize_database()
    clear_existing_data()

    auth = AuthManager()
    manager = SubscriptionManager()
    today = date.today()

    user_id, error = auth.register(DEMO_USERNAME, DEMO_PASSWORD)
    if error:
        print(f"Could not create demo account: {error}")
        return

    sample_subscriptions = [
        Subscription(id=None, user_id=user_id, service_name="Netflix", category="Streaming",
                     cost=549.00, billing_cycle="Monthly",
                     next_renewal_date=(today + timedelta(days=3)).isoformat(), status="Active"),
        Subscription(id=None, user_id=user_id, service_name="Spotify", category="Music",
                     cost=149.00, billing_cycle="Monthly",
                     next_renewal_date=(today + timedelta(days=5)).isoformat(), status="Active"),
        Subscription(id=None, user_id=user_id, service_name="Canva Pro", category="Productivity",
                     cost=2399.00, billing_cycle="Yearly",
                     next_renewal_date=(today + timedelta(days=20)).isoformat(), status="Active"),
        Subscription(id=None, user_id=user_id, service_name="Google One", category="Cloud Storage",
                     cost=549.00, billing_cycle="Yearly",
                     next_renewal_date=(today + timedelta(days=200)).isoformat(), status="Active"),
        Subscription(id=None, user_id=user_id, service_name="Disney+", category="Streaming",
                     cost=299.00, billing_cycle="Monthly",
                     next_renewal_date=(today + timedelta(days=45)).isoformat(), status="Cancelled"),
    ]
    for sub in sample_subscriptions:
        manager.add_subscription(sub, user_id)

    print(f"Created demo account -> username: {DEMO_USERNAME}  password: {DEMO_PASSWORD}")
    print(f"Seeded {len(sample_subscriptions)} sample subscriptions.")


if __name__ == "__main__":
    seed()
