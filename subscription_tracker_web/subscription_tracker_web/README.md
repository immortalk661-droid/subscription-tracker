# Subscription Tracking System

A Python + Flask + SQLite web app for logging and monitoring recurring
subscriptions, with real user accounts. Built for SDF04 (Object-Oriented
Programming). Runs on both desktop and mobile browsers.

## Features
- **Accounts**: register, log in, log out — each account only sees its own subscriptions
- **Profile**: change your password, or permanently delete your account (and all its subscriptions)
- Add, edit, cancel, and delete subscription records
- Filter by status (All / Active / Cancelled), search by service name
- Monthly/Yearly cost totals
- Renewal alert banner + red sidebar badge when something renews within 7 days
- Dedicated "Renewing Soon" page
- **Calendar** — monthly grid showing which day each subscription renews on
- **Reports** — cost breakdown by category + 6-month spending projection, as bar charts;
  export as CSV, or open a clean printable report page (Print dialog → Save as PDF)

## Project Structure
```
subscription_tracker_web/
├── app.py                     # Flask routes
├── database.py                # SQLite connection + table creation
├── models.py                  # User, Subscription classes
├── auth_manager.py            # AuthManager — register/login/change password/delete account
├── subscription_manager.py    # SubscriptionManager — all CRUD + calendar logic, per user
├── report_manager.py          # ReportManager — category breakdown + spending projection
├── seed.py                    # Demo account + sample data
├── templates/
│   ├── base.html                 # Sidebar + topbar shell
│   ├── login.html / register.html
│   ├── index.html                # Dashboard
│   ├── renewals.html             # Renewing Soon page
│   ├── form.html                 # Add / Edit form
│   ├── calendar.html             # Monthly renewal calendar
│   ├── reports.html              # Charts + export/print links
│   ├── reports_print.html        # Standalone printable report
│   ├── profile.html              # NEW — change password / delete account
│   └── _icons.html               # Reusable inline SVG icons
├── static/style.css
├── requirements.txt
└── README.md
```

### Why each manager only touches its own table
AuthManager only ever runs SQL against `users`; SubscriptionManager
only ever runs SQL against `subscriptions`; ReportManager doesn't
touch the database at all — it calls SubscriptionManager's own
methods and does the math on top. That's why deleting an account is
two calls, not one: `SubscriptionManager.delete_all_for_user()`
cleans up that user's subscriptions, then `AuthManager.delete_account()`
removes the users row — each manager stays responsible for only its
own table.

## Setup
```
pip install -r requirements.txt
python seed.py
python app.py
```
Demo login: `demo` / `demo1234`

Two addresses print in the terminal — `127.0.0.1:5000` for your own
computer, and a `192.168.x.x:5000` one to open on your phone (same WiFi).
