from flask import Flask, render_template, request, jsonify
import threading
import time
import random
import requests
import re
import concurrent.futures
from fake_useragent import UserAgent

app = Flask(__name__)
ua = UserAgent()

# Global Controls
stop_event = threading.Event()
status = {
    "running": False,
    "sent": 0,
    "total": 0,
    "errors": 0,
    "last_error": "None",
    "proxies_loaded": 0,
    "finished": False
}

# High-quality free proxy sources
PROXY_SOURCES = [
    "https://spys.one/en/http-proxy-list/",
    "https://free-proxy-list.net/en/anonymous-proxy.html",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite&protocols=socks5&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=anonymous&limit=500&page=1&sort_by=lastChecked&sort_type=desc"
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite&speed=fast&limit=500&page=1&sort_by=lastChecked&sort_type=desc"
    "https://spys.one/en/anonymous-proxy-list/"
  "https://api.lumiproxy.com/web_v1/free-proxy/list?page_size=60&page=1&anonymity=2&language=en-us"
"https://api.lumiproxy.com/web_v1/free-proxy/list?page_size=60&page=1&protocol=2&anonymity=2&language=en-us"
]

def scrape_proxies():
    combined = []
    for url in PROXY_SOURCES:
        try:
            res = requests.get(url, timeout=5)
            found = re.findall(r'\d+\.\d+\.\d+\.\d+:\d+', res.text)
            combined.extend(found)
        except: continue
    return list(set(combined))

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/status")
def get_status():
    return jsonify(status)

@app.route("/stop", methods=["POST"])
def stop():
    stop_event.set()
    status["running"] = False
    return jsonify({"ok": True})

@app.route("/start", methods=["POST"])
def start():
    if status["running"]:
        return jsonify({"error": "Already running"})
    
    data = request.json
    stop_event.clear()
    status.update({
        "sent": 0, 
        "total": int(data.get("views", 0)), 
        "errors": 0, 
        "running": True, 
        "finished": False,
        "last_error": "None"
    })
    
    threading.Thread(target=manage_execution, args=(data.get("url"), status["total"])).start()
    return jsonify({"ok": True})

def persistent_request(url, proxies_list):
    """Retries with different proxies until success or the hard limit is hit."""
    # Safety: Stop if user hits stop OR if another thread already finished the job
    while not stop_event.is_set() and status["sent"] < status["total"]:
        proxy_str = random.choice(proxies_list) if proxies_list else None
        proxies = {"http": f"http://{proxy_str}", "https": f"http://{proxy_str}"}
        
        try:
            # Short timeout to skip dead proxies fast
            with requests.get(url, headers={"User-Agent": ua.random}, proxies=proxies, timeout=5, allow_redirects=True) as r:
                if r.status_code == 200:
                    # Thread-safe check before incrementing
                    if status["sent"] < status["total"]:
                        status["sent"] += 1
                        return True
                else:
                    status["errors"] += 1
        except:
            status["errors"] += 1
            
        time.sleep(0.01) # Small pause to prevent CPU locking
    return False

def manage_execution(url, total):
    global status
    proxies = scrape_proxies()
    status["proxies_loaded"] = len(proxies)

    if not proxies:
        status["running"] = False
        status["last_error"] = "No proxies found"
        return

    # Use 50 workers for high-speed concurrency
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(persistent_request, url, proxies) for _ in range(total)]
        
        # Monitor threads and kill if limit reached
        for _ in concurrent.futures.as_completed(futures):
            if status["sent"] >= total or stop_event.is_set():
                stop_event.set() # Trigger immediate stop for all active loops
                break

    status["running"] = False
    if status["sent"] >= total:
        status["finished"] = True

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)