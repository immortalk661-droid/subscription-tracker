"""
app.py
------
Flask routes. Business logic lives in AuthManager, SubscriptionManager,
and ReportManager — routes only call their methods, never write SQL.
"""

import csv
import io
from calendar import monthrange, month_name
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, Response
)

from database import initialize_database
from models import Subscription
from subscription_manager import SubscriptionManager
from auth_manager import AuthManager
from report_manager import ReportManager

import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("SECRET_KEY is not configured!")
initialize_database()

manager = SubscriptionManager()
auth = AuthManager()
reports = ReportManager()

CATEGORIES = ["Streaming", "Music", "Cloud Storage", "Productivity", "Gaming", "News", "Other"]
BILLING_CYCLES = ["Monthly", "Yearly"]

CATEGORY_STYLE = {
    "Streaming": {"gradient": "grad-streaming", "icon": "play"},
    "Music": {"gradient": "grad-music", "icon": "music"},
    "Cloud Storage": {"gradient": "grad-cloud", "icon": "cloud"},
    "Productivity": {"gradient": "grad-productivity", "icon": "edit"},
    "Gaming": {"gradient": "grad-gaming", "icon": "game"},
    "News": {"gradient": "grad-news", "icon": "news"},
    "Other": {"gradient": "grad-other", "icon": "box"},
}


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_globals():
    user_id = session.get("user_id")
    renewal_count = len(manager.get_upcoming_renewals(user_id, days_ahead=7)) if user_id else 0
    return {
        "category_style": CATEGORY_STYLE,
        "default_style": {"gradient": "grad-other", "icon": "box"},
        "renewal_count": renewal_count,
        "current_username": session.get("username"),
    }


@app.template_filter("days_until")
def days_until_filter(date_str):
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    return (target - datetime.now().date()).days


@app.template_filter("category_style_for")
def category_style_for_filter(category):
    return CATEGORY_STYLE.get(category, {"gradient": "grad-other", "icon": "box"})


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html", username=username)
        new_id, error = auth.register(username, password)
        if error:
            flash(error, "error")
            return render_template("register.html", username=username)
        session["user_id"] = new_id
        session["username"] = username.strip()
        flash(f"Welcome, {username.strip()}! Your account was created.", "success")
        return redirect(url_for("index"))
    return render_template("register.html", username="")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = auth.authenticate(username, password)
        if user is None:
            flash("Incorrect username or password.", "error")
            return render_template("login.html", username=username)
        session["user_id"] = user.id
        session["username"] = user.username
        return redirect(url_for("index"))
    return render_template("login.html", username="")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You've been logged out.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Profile (NEW)
# ---------------------------------------------------------------------------
@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", active_page="profile")


@app.route("/profile/password", methods=["POST"])
@login_required
def profile_change_password():
    user_id = session["user_id"]
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if new_password != confirm_password:
        flash("New passwords do not match.", "error")
        return redirect(url_for("profile"))

    success, error = auth.change_password(user_id, current_password, new_password)
    if not success:
        flash(error, "error")
    else:
        flash("Your password was changed.", "success")
    return redirect(url_for("profile"))


@app.route("/profile/delete", methods=["POST"])
@login_required
def profile_delete_account():
    user_id = session["user_id"]
    typed_username = request.form.get("confirm_username", "")

    if typed_username != session.get("username"):
        flash("Type your exact username to confirm account deletion.", "error")
        return redirect(url_for("profile"))

    # SubscriptionManager cleans up this user's subscriptions; AuthManager
    # removes the users row — each manager only touches its own table.
    manager.delete_all_for_user(user_id)
    auth.delete_account(user_id)
    session.clear()
    flash("Your account and all its subscriptions were deleted.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Subscription routes
# ---------------------------------------------------------------------------
@app.route("/")
@login_required
def index():
    user_id = session["user_id"]
    status_filter = request.args.get("status", "All")
    search_query = request.args.get("q", "").strip()

    subscriptions = manager.get_all_subscriptions(user_id, status_filter=status_filter)
    if search_query:
        subscriptions = [s for s in subscriptions if search_query.lower() in s.service_name.lower()]

    upcoming = manager.get_upcoming_renewals(user_id, days_ahead=7)
    monthly_total = manager.get_total_monthly_cost(user_id)
    yearly_total = manager.get_total_yearly_cost(user_id)

    return render_template(
        "index.html", subscriptions=subscriptions, status_filter=status_filter,
        search_query=search_query, upcoming=upcoming, monthly_total=monthly_total,
        yearly_total=yearly_total, today=datetime.now().date(), active_page="dashboard",
    )


@app.route("/renewals")
@login_required
def renewals():
    user_id = session["user_id"]
    upcoming = manager.get_upcoming_renewals(user_id, days_ahead=7)
    return render_template("renewals.html", upcoming=upcoming, active_page="renewals")


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    user_id = session["user_id"]
    if request.method == "POST":
        sub, error = _read_form_as_subscription()
        if error:
            flash(error, "error")
            return render_template("form.html", mode="add", categories=CATEGORIES,
                                    billing_cycles=BILLING_CYCLES, sub=request.form, active_page="add")
        manager.add_subscription(sub, user_id)
        flash(f'"{sub.service_name}" was added.', "success")
        return redirect(url_for("index"))
    return render_template("form.html", mode="add", categories=CATEGORIES,
                            billing_cycles=BILLING_CYCLES, sub=None, active_page="add")


@app.route("/edit/<int:sub_id>", methods=["GET", "POST"])
@login_required
def edit(sub_id):
    user_id = session["user_id"]
    existing = manager.get_subscription_by_id(sub_id, user_id)
    if existing is None:
        flash("That subscription no longer exists.", "error")
        return redirect(url_for("index"))
    if request.method == "POST":
        sub, error = _read_form_as_subscription()
        if error:
            flash(error, "error")
            return render_template("form.html", mode="edit", categories=CATEGORIES,
                                    billing_cycles=BILLING_CYCLES, sub=request.form, sub_id=sub_id, active_page="add")
        sub.id = sub_id
        sub.status = existing.status
        manager.update_subscription(sub, user_id)
        flash(f'"{sub.service_name}" was updated.', "success")
        return redirect(url_for("index"))
    return render_template("form.html", mode="edit", categories=CATEGORIES,
                            billing_cycles=BILLING_CYCLES, sub=existing, sub_id=sub_id, active_page="add")


@app.route("/cancel/<int:sub_id>", methods=["POST"])
@login_required
def cancel(sub_id):
    manager.cancel_subscription(sub_id, session["user_id"])
    flash("Subscription marked as Cancelled.", "success")
    return redirect(url_for("index"))


@app.route("/delete/<int:sub_id>", methods=["POST"])
@login_required
def delete(sub_id):
    manager.delete_subscription(sub_id, session["user_id"])
    flash("Subscription deleted.", "success")
    return redirect(url_for("index"))


def _read_form_as_subscription():
    service_name = request.form.get("service_name", "").strip()
    category = request.form.get("category", "").strip()
    cost_text = request.form.get("cost", "").strip()
    billing_cycle = request.form.get("billing_cycle", "").strip()
    renewal_date = request.form.get("next_renewal_date", "").strip()
    notes = request.form.get("notes", "").strip()

    if not service_name:
        return None, "Please enter a service name."
    try:
        cost = float(cost_text)
        if cost < 0:
            raise ValueError
    except ValueError:
        return None, "Please enter a valid, non-negative cost."
    try:
        datetime.strptime(renewal_date, "%Y-%m-%d")
    except ValueError:
        return None, "Please enter the next renewal date as YYYY-MM-DD."

    sub = Subscription(
        id=None, user_id=session.get("user_id"), service_name=service_name, category=category,
        cost=cost, billing_cycle=billing_cycle, next_renewal_date=renewal_date, status="Active", notes=notes,
    )
    return sub, None


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------
@app.route("/calendar")
@login_required
def calendar_view():
    user_id = session["user_id"]
    today = datetime.now().date()
    year = request.args.get("year", type=int, default=today.year)
    month = request.args.get("month", type=int, default=today.month)
    if month < 1:
        month, year = 12, year - 1
    elif month > 12:
        month, year = 1, year + 1

    first_weekday, days_in_month = monthrange(year, month)
    first_weekday = (first_weekday + 1) % 7

    renewals_by_day = manager.get_renewals_for_month(user_id, year, month)

    weeks = []
    day_counter = 1 - first_weekday
    while day_counter <= days_in_month:
        week = []
        for _ in range(7):
            if 1 <= day_counter <= days_in_month:
                week.append({
                    "day": day_counter,
                    "subs": renewals_by_day.get(day_counter, []),
                    "is_today": (year, month, day_counter) == (today.year, today.month, today.day),
                })
            else:
                week.append(None)
            day_counter += 1
        weeks.append(week)

    prev_month, prev_year = (12, year - 1) if month == 1 else (month - 1, year)
    next_month, next_year = (1, year + 1) if month == 12 else (month + 1, year)

    return render_template(
        "calendar.html", weeks=weeks, month_label=f"{month_name[month]} {year}",
        year=year, month=month, prev_month=prev_month, prev_year=prev_year,
        next_month=next_month, next_year=next_year, active_page="calendar",
    )


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
@app.route("/reports")
@login_required
def reports_view():
    user_id = session["user_id"]
    breakdown = reports.get_category_breakdown(user_id)
    projection = reports.get_monthly_projection(user_id, months_ahead=6)
    max_category = max([v for _, v in breakdown], default=0)
    max_projection = max([v for _, v in projection], default=0)
    return render_template(
        "reports.html", breakdown=breakdown, projection=projection,
        max_category=max_category or 1, max_projection=max_projection or 1,
        active_page="reports",
    )


@app.route("/reports/print")
@login_required
def reports_print():
    user_id = session["user_id"]
    subscriptions = manager.get_all_subscriptions(user_id)
    breakdown = reports.get_category_breakdown(user_id)
    monthly_total = manager.get_total_monthly_cost(user_id)
    yearly_total = manager.get_total_yearly_cost(user_id)
    return render_template(
        "reports_print.html", subscriptions=subscriptions, breakdown=breakdown,
        monthly_total=monthly_total, yearly_total=yearly_total,
        username=session.get("username"), generated_on=datetime.now().strftime("%B %d, %Y"),
    )


@app.route("/reports/export.csv")
@login_required
def reports_export_csv():
    user_id = session["user_id"]
    subscriptions = manager.get_all_subscriptions(user_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Service Name", "Category", "Cost", "Billing Cycle", "Next Renewal Date", "Status", "Notes"])
    for sub in subscriptions:
        writer.writerow([sub.service_name, sub.category, sub.cost, sub.billing_cycle,
                          sub.next_renewal_date, sub.status, sub.notes])

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=subscriptions.csv"},
    )


if __name__ == "__main__":
    initialize_database()
    app.run(host="0.0.0.0", port=5000, debug=True)
