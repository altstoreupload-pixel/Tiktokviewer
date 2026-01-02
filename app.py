import os
import re
import random
import threading
import time
from flask import Flask, render_template, request, jsonify
from curl_cffi import requests

app = Flask(__name__)

stats = {
    "sent": 0, "total": 0, "errors": 0, 
    "proxies_loaded": 0, "running": False, "finished": False
}

MASTER_PROXIES = []

def scrape_and_save():
    """Fetches proxies from URLs, extracts them via Regex, and saves to proxies.txt."""
    global MASTER_PROXIES
    
    # 1. Start with what's already in the file
    existing_proxies = set()
    if os.path.exists("proxies.txt"):
        with open("proxies.txt", "r") as f:
            existing_proxies = {line.strip() for line in f if line.strip()}

    # 2. Scrape the URLs
    sources = [
   "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://www.proxyscan.io/download?type=http",
    "https://spys.me/proxy.txt",
    "https://spys.one/en/http-proxy-list/",
    "https://free-proxy-list.net/en/anonymous-proxy.html",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite&protocols=socks5&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=anonymous&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite&speed=fast&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://spys.one/en/anonymous-proxy-list/",
    "https://api.lumiproxy.com/web_v1/free-proxy/list?page_size=60&page=1&anonymity=2&language=en-us",
    "https://api.lumiproxy.com/web_v1/free-proxy/list?page_size=60&page=1&protocol=2&anonymity=2&language=en-us"
    ]

    scraped_count = 0
    # Pattern to find IP:PORT (e.g. 192.168.1.1:8080)
    proxy_pattern = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}')

    for url in sources:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                found = proxy_pattern.findall(r.text)
                for p in found:
                    if p not in existing_proxies:
                        existing_proxies.add(p)
                        scraped_count += 1
        except:
            continue

    # 3. Update the file with the NEW combined list
    MASTER_PROXIES = list(existing_proxies)
    with open("proxies.txt", "w") as f:
        f.write("\n".join(MASTER_PROXIES))
    
    stats["proxies_loaded"] = len(MASTER_PROXIES)
    print(f"DEBUG: Added {scraped_count} new proxies. Total database: {len(MASTER_PROXIES)}")

def worker_logic(target_url, total_views):
    global stats
    scrape_and_save() # Automatically scrape and save to file every time you start
    
    if not MASTER_PROXIES:
        stats["running"] = False
        return

    for _ in range(total_views):
        if not stats["running"]: break
            
        success = False
        retries = 0
        
        while not success and retries < 2:
            proxy = random.choice(MASTER_PROXIES)
            proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            
            try:
                resp = requests.get(
                    target_url, 
                    proxies=proxies, 
                    impersonate="chrome110", 
                    timeout=10
                )
                if resp.status_code in [200, 204]:
                    stats["sent"] += 1
                    success = True
                else:
                    stats["errors"] += 1
                    retries += 1
            except:
                stats["errors"] += 1
                retries += 1
        
        time.sleep(0.01)

    stats["running"] = False
    stats["finished"] = True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    data = request.json
    if stats["running"]: return jsonify({"ok": False})
    
    stats.update({"sent": 0, "errors": 0, "total": int(data.get("views", 0)), "running": True, "finished": False})
    threading.Thread(target=worker_logic, args=(data.get("url"), stats["total"])).start()
    return jsonify({"ok": True})

@app.route('/status')
def get_status():
    return jsonify(stats)

@app.route('/stop', methods=['POST'])
def stop():
    stats["running"] = False
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
