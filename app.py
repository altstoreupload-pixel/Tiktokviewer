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

# Global status tracking
status = {
    "running": False,
    "sent": 0,
    "total": 0
}

def load_proxies():
    """Reads proxies from proxies.txt and cleans them."""
    try:
        with open("proxies.txt", "r") as f:
            # Filters out empty lines and comments
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
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

    # Launch background thread to manage the execution pool
    thread = threading.Thread(target=manage_execution, args=(url, total))
    thread.start()

    return jsonify({"ok": True})

def send_single_request(url, proxies_list):
    """
    Simulates a unique browser user.
    Uses random User-Agents, unique UUIDs, and proxy rotation.
    """
    proxy_str = random.choice(proxies_list) if proxies_list else None
    proxies = {"http": proxy_str, "https": proxy_str} if proxy_str else None
    
    # Advanced Headers to mimic a real web browser
    headers = {
        "User-Agent": ua.random,
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": url.split('/')[2] if '/' in url else "",
        "Referer": url,
        "X-Requested-With": "XMLHttpRequest"
    }

    # Unique payload mimicking the bypass script's UUID usage
    payload = {
        "session_id": str(uuid.uuid4()),
        "device_id": str(uuid.uuid4()),
        "timestamp": int(time.time()),
        "action": "view"
    }

    try:
        # 10-second timeout ensures dead proxies don't hang the worker
        response = requests.post(url, json=payload, headers=headers, proxies=proxies, timeout=10)
        
        # Check for 200 OK and handle potential "wait" responses from the server
        if response.status_code == 200:
            res_json = response.json()
            # If the server provides a cooldown timestamp, we could log it here
            return True
    except:
        pass
    return False

def manage_execution(url, total):
    """Manages the thread pool and updates progress."""
    global status
    proxies_list = load_proxies()
    status["running"] = True
    status["sent"] = 0
    status["total"] = total

    # Use 10 threads to send requests concurrently (similar to the bypass script)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Create a list of tasks
        futures = {executor.submit(send_single_request, url, proxies_list): i for i in range(total)}
        
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                status["sent"] += 1
            
            # Add 'jitter' - small random delays to look more human
            time.sleep(random.uniform(0.05, 0.15))

    status["running"] = False

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)