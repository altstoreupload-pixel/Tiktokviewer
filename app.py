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

PROXY_SOURCES = [
    "https://spys.one/en/http-proxy-list/",
    "https://free-proxy-list.net/en/anonymous-proxy.html",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite&protocols=socks5&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=anonymous&limit=500&page=1&sort_by=lastChecked&sort_type=desc"
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
        "sent": 0, "total": int(data.get("views", 0)), 
        "errors": 0, "running": True, "finished": False
    })
    
    threading.Thread(target=manage_execution, args=(data.get("url"), status["total"])).start()
    return jsonify({"ok": True})

def persistent_request(url, proxies_list):
    """Retries with different proxies until ONE success is achieved."""
    while not stop_event.is_set():
        proxy_str = random.choice(proxies_list) if proxies_list else None
        proxies = {"http": f"http://{proxy_str}", "https": f"http://{proxy_str}"}
        
        try:
            with requests.get(url, headers={"User-Agent": ua.random}, proxies=proxies, timeout=5, allow_redirects=True) as r:
                if r.status_code == 200:
                    status["sent"] += 1
                    return True
                else:
                    status["errors"] += 1
                    status["last_error"] = f"HTTP {r.status_code}"
        except Exception as e:
            status["errors"] += 1
            status["last_error"] = "Proxy Failed/Timed Out"
            
        # Optional: tiny delay between retries to prevent local CPU spike
        time.sleep(0.01)
    return False

def manage_execution(url, total):
    global status
    proxies = scrape_proxies()
    status["proxies_loaded"] = len(proxies)

    if not proxies:
        status["running"] = False
        status["last_error"] = "No proxies found"
        return

    # Using 100 workers for maximum speed through bad proxies
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(persistent_request, url, proxies) for _ in range(total)]
        concurrent.futures.wait(futures)

    status["running"] = False
    if not stop_event.is_set():
        status["finished"] = True

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)