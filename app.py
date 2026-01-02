from flask import Flask, render_template, request, jsonify
import threading
import time
import random
import requests
import uuid
import concurrent.futures
from fake_useragent import UserAgent

app = Flask(__name__)
ua = UserAgent()

# CONFIGURATION: Set your proxy link here
PROXY_LIST_URL = "https://advanced.name/freeproxy/6957799dd74e6?type=https"

# Global state
status = {
    "running": False,
    "sent": 0,
    "total": 0
}

def load_proxies_from_url():
    """Fetches a list of proxies from a remote URL."""
    try:
        response = requests.get(PROXY_LIST_URL, timeout=10)
        if response.status_code == 200:
            # Clean and filter the list
            return [line.strip() for line in response.text.splitlines() if line.strip() and not line.startswith("#")]
        return []
    except Exception as e:
        print(f"Error fetching proxies: {e}")
        return []

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

    # Launch background thread to handle the request pool
    thread = threading.Thread(target=manage_execution, args=(url, total))
    thread.start()

    return jsonify({"ok": True})

def send_single_request(url, proxies_list):
    """Mimics a unique human browser user."""
    proxy_str = random.choice(proxies_list) if proxies_list else None
    proxies = {"http": proxy_str, "https": proxy_str} if proxy_str else None
    
    # Advanced Browser Fingerprint
    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1", # Do Not Track
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://www.google.com/",
        "X-Request-ID": str(uuid.uuid4())
    }

    # Unique payload data for the target
    payload = {
        "session_id": str(uuid.uuid4()),
        "client_timestamp": int(time.time()),
        "platform": "web_desktop"
    }

    try:
        # Use 10s timeout to avoid hanging on slow proxies
        response = requests.post(url, json=payload, headers=headers, proxies=proxies, timeout=10)
        return response.ok
    except:
        return False

def manage_execution(url, total):
    global status
    # Fetch fresh proxies from your link at the start of the run
    proxies_list = load_proxies_from_url()
    
    status["running"] = True
    status["sent"] = 0
    status["total"] = total

    # workers=10 allows for high concurrency (multitasking)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_single_request, url, proxies_list) for _ in range(total)]
        
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                status["sent"] += 1
            
            # Tiny random jitter to break the "robotic" pattern
            time.sleep(random.uniform(0.01, 0.05))

    status["running"] = False

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)