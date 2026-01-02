from flask import Flask, render_template, request, jsonify
import threading
import time
import random
import requests
import uuid
import concurrent.futures
import re
from fake_useragent import UserAgent

app = Flask(__name__)
ua = UserAgent()

# Shared state for tracking progress
status = {
    "running": False,
    "sent": 0,
    "total": 0,
    "errors": 0,
    "last_error": "None",
    "proxies_loaded": 0
}

# High-frequency proxy sources
PROXY_SOURCES = [
     "https://spys.one/en/http-proxy-list/",
    "https://free-proxy-list.net/en/anonymous-proxy.html",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite&protocols=socks5&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=anonymous&limit=500&page=1&sort_by=lastChecked&sort_type=desc"
]

def scrape_proxies():
    """Aggregates proxies from multiple open-source repositories."""
    combined = []
    for url in PROXY_SOURCES:
        try:
            res = requests.get(url, timeout=5)
            found = re.findall(r'\d+\.\d+\.\d+\.\d+:\d+', res.text)
            combined.extend(found)
        except: 
            continue
    return list(set(combined))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/status")
def get_status():
    """Returns the current progress to the frontend."""
    return jsonify({**status, "timestamp": time.time()})

@app.route("/start", methods=["POST"])
def start():
    if status["running"]:
        return jsonify({"error": "Already running"})
    
    data = request.json
    url = data.get("url")
    total = int(data.get("views", 0))
    
    # Reset status for new run
    status.update({"sent": 0, "total": total, "errors": 0, "running": True})
    
    threading.Thread(target=manage_execution, args=(url, total)).start()
    return jsonify({"ok": True})

def send_single_request(url, proxies_list):
    """Executes a single view with a rotating proxy and User-Agent."""
    proxy_str = random.choice(proxies_list) if proxies_list else None
    proxies = {"http": f"http://{proxy_str}", "https": f"http://{proxy_str}"} if proxy_str else None
    headers = {"User-Agent": ua.random}
    
    try:
        # 5s timeout to prevent slow proxies from bottlenecking speed
        resp = requests.get(url, headers=headers, proxies=proxies, timeout=5, allow_redirects=True)
        return resp.ok, None
    except Exception as e:
        return False, str(e)

def manage_execution(url, total):
    """Manages high-speed concurrent execution."""
    global status
    proxies_list = scrape_proxies()
    status["proxies_loaded"] = len(proxies_list)

    # SPEED UP: Increased to 50 concurrent workers
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(send_single_request, url, proxies_list) for _ in range(total)]
        
        for future in concurrent.futures.as_completed(futures):
            success, err = future.result()
            if success:
                status["sent"] += 1
            else:
                status["errors"] += 1
                status["last_error"] = err

    status["running"] = False

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)