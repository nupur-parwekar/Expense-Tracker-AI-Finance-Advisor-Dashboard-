from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests

app = Flask(__name__, static_folder=".")
CORS(app)

API_KEY = "YOUR_OPENROUTER_API_KEY"   # 🔴 paste your key here

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    context = data.get("context", {})

    prompt = f"""
    You are a smart Indian finance advisor.
    Give short, practical advice (2-3 lines max).

    User Data:
    Name: {context.get('name')}
    Salary: ₹{context.get('salary')}
    Expenses: ₹{context.get('total_expenses')}
    Remaining: ₹{context.get('remaining')}
    Category: {context.get('category_breakdown')}

    Question: {user_message}
    """

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mistral-7b-instruct",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
        )

        result = response.json()
        reply = result["choices"][0]["message"]["content"]

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(debug=True)
