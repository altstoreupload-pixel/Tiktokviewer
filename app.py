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
status_lock = threading.Lock() # Prevents multiple threads from updating the counter at once
stop_event = threading.Event()

status = {
    "running": False,
    "sent": 0,
    "total": 0,
    "errors": 0,
    "finished": False,
    "proxies_loaded": 0
}

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
    with status_lock:
        return jsonify(status)

@app.route("/stop", methods=["POST"])
def stop():
    stop_event.set()
    with status_lock:
        status["running"] = False
    return jsonify({"ok": True})

@app.route("/start", methods=["POST"])
def start():
    if status["running"]:
        return jsonify({"error": "Already running"})
    
    data = request.json
    stop_event.clear()
    
    with status_lock:
        status.update({
            "sent": 0, 
            "total": int(data.get("views", 0)), 
            "errors": 0, 
            "running": True, 
            "finished": False
        })
    
    threading.Thread(target=manage_execution, args=(data.get("url"), status["total"])).start()
    return jsonify({"ok": True})

def persistent_request(url, proxies_list):
    """Retries until a successful hit is recorded or system is stopped."""
    while not stop_event.is_set():
        # Hard check: stop if we already reached the goal
        with status_lock:
            if status["sent"] >= status["total"]:
                return True

        proxy = random.choice(proxies_list) if proxies_list else None
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        
        try:
            r = requests.get(url, headers={"User-Agent": ua.random}, proxies=proxies, timeout=5, allow_redirects=True)
            if r.status_code == 200:
                with status_lock:
                    if status["sent"] < status["total"]:
                        status["sent"] += 1
                        return True # Exit loop on success
            else:
                with status_lock: status["errors"] += 1
        except:
            with status_lock: status["errors"] += 1
        
        time.sleep(0.01)
    return False

def manage_execution(url, total):
    global status
    proxies = scrape_proxies()
    with status_lock:
        status["proxies_loaded"] = len(proxies)

    # 50 workers for high speed
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(persistent_request, url, proxies) for _ in range(total)]
        
        # Monitor for completion
        for _ in concurrent.futures.as_completed(futures):
            with status_lock:
                if status["sent"] >= total or stop_event.is_set():
                    stop_event.set() # Kill remaining retries
                    break

    with status_lock:
        status["running"] = False
        if status["sent"] >= total:
            status["finished"] = True

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
