from flask import Flask, request, jsonify, send_from_directory
import threading
import time
import os

app = Flask(__name__, static_folder="static")

# Global state
state = {
    "running": False,
    "progress": 0,
    "total": 0
}

def simulate_views(target_url, total_views):
    state["running"] = True
    state["progress"] = 0
    state["total"] = total_views

    for i in range(total_views):
        time.sleep(0.5)  # simulate sending a view
        state["progress"] += 1

    state["running"] = False

# Serve frontend
@app.route("/")
def home():
    return send_from_directory("static", "index.html")

# API to start simulation
@app.route("/start", methods=["POST"])
def start():
    if state["running"]:
        return jsonify({"error": "Already running"}), 400

    data = request.json
    target_url = data.get("url")
    views = int(data.get("views", 0))

    if not target_url or views <= 0:
        return jsonify({"error": "Invalid input"}), 400

    thread = threading.Thread(
        target=simulate_views,
        args=(target_url, views),
        daemon=True
    )
    thread.start()

    return jsonify({"message": "Started"})

# API to check progress
@app.route("/progress")
def progress():
    return jsonify(state)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
