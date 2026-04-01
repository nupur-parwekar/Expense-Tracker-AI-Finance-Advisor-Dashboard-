

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import datetime
import uuid
import anthropic

app = Flask(__name__, static_folder="static")
CORS(app)

DATA_FILE = "expenses.json"


def load_expenses():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_expenses(expenses):
    with open(DATA_FILE, "w") as f:
        json.dump(expenses, f, indent=2)

def compute_stats(expenses):
    if not expenses:
        return {"total": 0, "by_category": {}, "by_month": {}, "count": 0}

    total = sum(e["amount"] for e in expenses)
    by_category = {}
    by_month = {}

    for e in expenses:
        cat = e.get("category", "Other")
        by_category[cat] = by_category.get(cat, 0) + e["amount"]

        month = e["date"][:7]  # YYYY-MM
        by_month[month] = by_month.get(month, 0) + e["amount"]

    return {
        "total": round(total, 2),
        "by_category": {k: round(v, 2) for k, v in by_category.items()},
        "by_month": {k: round(v, 2) for k, v in sorted(by_month.items())},
        "count": len(expenses),
        "average": round(total / len(expenses), 2),
    }



@app.route("/api/expenses", methods=["GET"])
def get_expenses():
    expenses = load_expenses()
    # Optional filters
    category = request.args.get("category")
    month    = request.args.get("month")
    if category:
        expenses = [e for e in expenses if e.get("category") == category]
    if month:
        expenses = [e for e in expenses if e["date"].startswith(month)]
    expenses.sort(key=lambda e: e["date"], reverse=True)
    return jsonify(expenses)

@app.route("/api/expenses", methods=["POST"])
def add_expense():
    data = request.json
    if not data or not data.get("amount") or not data.get("description"):
        return jsonify({"error": "amount and description are required"}), 400

    expense = {
        "id":          str(uuid.uuid4()),
        "amount":      float(data["amount"]),
        "description": data["description"],
        "category":    data.get("category", "Other"),
        "date":        data.get("date", datetime.date.today().isoformat()),
        "note":        data.get("note", ""),
        "created_at":  datetime.datetime.utcnow().isoformat(),
    }

    expenses = load_expenses()
    expenses.append(expense)
    save_expenses(expenses)
    return jsonify(expense), 201

@app.route("/api/expenses/<expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    expenses = load_expenses()
    original = len(expenses)
    expenses = [e for e in expenses if e["id"] != expense_id]
    if len(expenses) == original:
        return jsonify({"error": "not found"}), 404
    save_expenses(expenses)
    return jsonify({"deleted": expense_id})

@app.route("/api/expenses/<expense_id>", methods=["PUT"])
def update_expense(expense_id):
    expenses = load_expenses()
    data = request.json
    for e in expenses:
        if e["id"] == expense_id:
            e["amount"]      = float(data.get("amount", e["amount"]))
            e["description"] = data.get("description", e["description"])
            e["category"]    = data.get("category",    e["category"])
            e["date"]        = data.get("date",         e["date"])
            e["note"]        = data.get("note",         e.get("note", ""))
            save_expenses(expenses)
            return jsonify(e)
    return jsonify({"error": "not found"}), 404


@app.route("/api/stats", methods=["GET"])
def get_stats():
    expenses = load_expenses()
    return jsonify(compute_stats(expenses))



@app.route("/api/ai-advice", methods=["POST"])
def ai_advice():
    data     = request.json or {}
    question = data.get("question", "Give me a general financial overview and tips.")

    expenses = load_expenses()
    stats    = compute_stats(expenses)
    recent   = sorted(expenses, key=lambda e: e["date"], reverse=True)[:20]

    context = f"""
You are a friendly, expert personal finance advisor.
The user's expense data (last 20 transactions shown):
{json.dumps(recent, indent=2)}

Summary statistics:
- Total spent: ${stats['total']}
- Number of transactions: {stats['count']}
- Average per transaction: ${stats.get('average', 0)}
- Spending by category: {json.dumps(stats['by_category'])}
- Spending by month: {json.dumps(stats['by_month'])}

Answer the user's question concisely with actionable advice.
Use plain text (no markdown). Be warm but direct.
"""

    try:
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=600,
            system=context,
            messages=[{"role": "user", "content": question}],
        )
        reply = message.content[0].text
    except Exception as err:
        reply = f"AI advisor unavailable: {err}. Please check your ANTHROPIC_API_KEY."

    return jsonify({"advice": reply})



@app.route("/")
def index():
    return send_from_directory("static", "index.html")

if __name__ == "__main__":
    os.makedirs("static", exist_ok=True)
    app.run(debug=True, port=5000)
