from flask import Flask, render_template, request, jsonify
import threading
import time
import random
import requests

app = Flask(__name__)

# =========================
# LOAD PROXIES FROM FILE
# =========================
def load_proxies():
    try:
        with open("proxies.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

PROXIES = load_proxies()

status = {
    "running": False,
    "sent": 0,
    "total": 0
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/status")
def get_status():
    return jsonify(status)


@app.route("/start", methods=["POST"])
def start():
    if status["running"]:
        return jsonify({"error": "Already running"})

    data = request.json
    url = data.get("url")
    total = int(data.get("views", 0))

    if not url or total <= 0:
        return jsonify({"error": "Invalid input"})

    thread = threading.Thread(target=send_requests, args=(url, total))
    thread.start()

    return jsonify({"ok": True})


def send_requests(url, total):
    global PROXIES
    PROXIES = load_proxies()  # reload every run

    status["running"] = True
    status["sent"] = 0
    status["total"] = total

    for _ in range(total):
        proxy = random.choice(PROXIES) if PROXIES else None
        proxies = {"http": proxy, "https": proxy} if proxy else None

        try:
            requests.get(url, proxies=proxies, timeout=5)
            status["sent"] += 1
        except:
            pass

        time.sleep(0.1)

    status["running"] = False


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
