from flask import Flask, render_template, request, jsonify
import threading
import time
import random
import re
import concurrent.futures
from curl_cffi import requests
from fake_useragent import UserAgent

app = Flask(__name__)
ua = UserAgent()

status_lock = threading.Lock()
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

# Real-world referral sources to mimic organic discovery
REFERRERS = [
    "https://www.google.com/search?q=tiktok+trending",
    "https://www.tiktok.com/discover?lang=en",
    "https://www.tiktok.com/search?q=foryou",
    "https://www.tiktok.com/@ahmed_elfallah",
    "https://web.whatsapp.com/",
    "https://www.youtube.com",
    "https://linktr.ee/",
    "https://t.co/", # Twitter/X shortener
    "https://www.facebook.com/"
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
def index(): return render_template("index.html")

@app.route("/status")
def get_status():
    with status_lock: return jsonify(status)

@app.route("/stop", methods=["POST"])
def stop():
    stop_event.set()
    with status_lock: status["running"] = False
    return jsonify({"ok": True})

@app.route("/start", methods=["POST"])
def start():
    if status["running"]: return jsonify({"error": "Already running"})
    data = request.json
    stop_event.clear()
    with status_lock:
        status.update({"sent": 0, "total": int(data.get("views", 0)), "errors": 0, "running": True, "finished": False})
    threading.Thread(target=manage_execution, args=(data.get("url"), status["total"])).start()
    return jsonify({"ok": True})

def human_worker(url, proxies_list):
    """Mimics a human visitor using TLS 1.3, Headers, and Referrers."""
    while not stop_event.is_set():
        with status_lock:
            if status["sent"] >= status["total"]: return True

        proxy = random.choice(proxies_list) if proxies_list else None
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        
        # Random human headers
        headers = {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(["en-US,en;q=0.9", "en-GB,en;q=0.8", "en-CA,en;q=0.9"]),
            "Referer": random.choice(REFERRERS),
            "DNT": "1", # Do Not Track header often set by privacy-conscious users
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Upgrade-Insecure-Requests": "1"
        }

        try:
            # impersonate="chrome110" handles the TLS Fingerprint bypass
            r = requests.get(
                url, 
                headers=headers,
                proxies=proxies,
                timeout=12,
                impersonate="chrome110" 
            )
            
            if r.status_code in [200, 204]:
                with status_lock:
                    if status["sent"] < status["total"]:
                        status["sent"] += 1
                        if status["sent"] >= status["total"]: stop_event.set()
                        return True
            else:
                with status_lock: status["errors"] += 1
        except:
            with status_lock: status["errors"] += 1
        
        # Human-like thinking time/pause between retries
        time.sleep(random.uniform(0.1, 0.5))
    return False

def manage_execution(url, total):
    global status
    proxies = scrape_proxies()
    with status_lock: status["proxies_loaded"] = len(proxies)

    # Use a lower worker count for higher quality. 
    # High speed = High detection. Quality over quantity.
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(human_worker, url, proxies) for _ in range(total)]
        concurrent.futures.wait(futures)

    with status_lock:
        status["running"] = False
        if status["sent"] >= total: status["finished"] = True

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
