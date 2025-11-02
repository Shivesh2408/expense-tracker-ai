from datetime import date
from typing import Optional

from flask import Flask, render_template, request, redirect, url_for, flash

from db import ExpenseDB
from categorizer import CategoryRules
from predictor import Predictor


app = Flask(__name__)
app.secret_key = "dev-secret"

db = ExpenseDB(db_path="expenses.db")
rules = CategoryRules(path="categories.json")
predictor = Predictor(db)


@app.route("/")
def index():
    summary_month = db.get_summary("month")
    expenses = db.list_expenses(limit=5)
    forecast = predictor.predict_next_month()
    return render_template(
        "index.html",
        summary=summary_month,
        expenses=expenses,
        forecast=forecast,
    )


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        amount = float(request.form.get("amount", "0") or 0)
        description = request.form.get("description", "").strip()
        date_iso = request.form.get("date", date.today().isoformat())
        category = request.form.get("category", "")
        if not category:
            category = rules.categorize(description)
        if amount <= 0 or not description:
            flash("Please provide a valid amount and description.")
            return redirect(url_for("add"))
        db.add_expense(date_iso=date_iso, amount=amount, description=description, category=category)
        flash("Expense added!")
        return redirect(url_for("index"))
    return render_template("add.html", today=date.today().isoformat())


@app.route("/list")
def list_expenses():
    category = request.args.get("category")
    start = request.args.get("start")
    end = request.args.get("end")
    expenses = db.list_expenses(start_date=start or None, end_date=end or None, category=category or None, limit=200)
    return render_template("list.html", expenses=expenses)


@app.route("/summary")
def summary():
    period = request.args.get("period", "month")
    summary_data = db.get_summary(period)
    return render_template("summary.html", period=period, summary=summary_data)


@app.route("/predict")
def predict():
    months = int(request.args.get("months", "6"))
    forecast = predictor.predict_next_month(months_back=months)
    return render_template("predict.html", months=months, forecast=forecast)


@app.route("/chat", methods=["GET", "POST"])
def chat():
    from bot import ChatBot

    response: Optional[str] = None
    user_text = ""
    if request.method == "POST":
        user_text = request.form.get("message", "").strip()
        if user_text:
            response = ChatBot(db=db, rules=rules).respond(user_text)
    return render_template("chat.html", user_text=user_text, response=response)


if __name__ == "__main__":
    import os
    port_str = os.environ.get("PORT", "5000")
    try:
        port = int(port_str)
    except ValueError:
        port = 5000
    print(f"Starting server on http://127.0.0.1:{port} (or http://localhost:{port})")
    app.run(host="0.0.0.0", port=port, debug=True)



