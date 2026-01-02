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

# FIXED: Added commas and high-capacity sources
PROXY_SOURCES = [
      "https://spys.one/en/http-proxy-list/",
    "https://free-proxy-list.net/en/anonymous-proxy.html",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite&protocols=socks5&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=anonymous&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite&speed=fast&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://spys.one/en/anonymous-proxy-list/",
    "https://api.lumiproxy.com/web_v1/free-proxy/list?page_size=60&page=1&anonymity=2&language=en-us",
    "https://api.lumiproxy.com/web_v1/free-proxy/list?page_size=60&page=1&protocol=2&anonymity=2&language=en-us",
    "https://88.198.212.91:3128",
    "https://89.43.31.134:3128",
    "https://47.90.149.238:1036",
    "https://8.213.215.187:8080",
    "https://8.213.215.187:9098",
    "https://8.213.156.191:8444",
    "https://47.92.82.167:7890",
    "https://47.91.120.190:8888",
    "https://47.252.11.233:1081",
    "https://39.102.213.3:9080",
    "https://47.252.11.233:1080",
    "https://168.195.214.41:8800",
    "https://8.215.3.250:80",
    "https://8.210.17.35:8082",
    "https://8.215.3.250:3128",
    "https://47.91.29.151:4002",
    "https://219.93.101.63:80",
    "https://112.198.132.199:8082",
    "https://47.90.149.238:9098",
    "https://103.118.85.144:8080",
    "https://8.213.222.247:6379",
    "https://103.156.14.227:8080",
    "https://47.237.107.41:3128",
    "https://8.220.136.174:4567",
    "https://157.10.89.203:8880",
    "https://43.230.129.23:8080",
    "https://87.239.31.42:80",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://www.proxyscan.io/download?type=http",
    "https://spys.me/proxy.txt",
    "https://8.220.204.215:9200"
]

# Real-world referral sources
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
    # Adding your manual list here first
    manual_ips = [
        "88.198.212.91:3128", "89.43.31.134:3128", "47.90.149.238:1036",
        "8.213.215.187:8080", "8.213.215.187:9098", "8.213.156.191:8444",
        "47.92.82.167:7890", "47.91.120.190:8888", "47.252.11.233:1081",
        "39.102.213.3:9080", "47.252.11.233:1080", "168.195.214.41:8800"
    ]
    combined.extend(manual_ips)

    for url in PROXY_SOURCES:
        try:
            # We use a longer timeout for scraping to get more results
            res = requests.get(url, timeout=10)
            found = re.findall(r'\d+\.\d+\.\d+\.\d+:\d+', res.text)
            combined.extend(found)
        except: continue
    
    # Remove duplicates
    final_list = list(set(combined))
    print(f"CRITICAL DEBUG: Total unique proxies loaded: {len(final_list)}", flush=True)
    return final_list

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
    while not stop_event.is_set():
        with status_lock:
            if status["sent"] >= status["total"]: return True

        proxy = random.choice(proxies_list) if proxies_list else None
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        
        headers = {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": random.choice(REFERRERS),
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
        }

        try:
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
        
        time.sleep(random.uniform(0.1, 0.4))
    return False

def manage_execution(url, total):
    global status
    proxies = scrape_proxies()
    with status_lock: status["proxies_loaded"] = len(proxies)

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(human_worker, url, proxies) for _ in range(total)]
        concurrent.futures.wait(futures)

    with status_lock:
        status["running"] = False
        if status["sent"] >= total: status["finished"] = True

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
