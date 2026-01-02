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

status = {
    "running": False,
    "sent": 0,
    "total": 0,
    "errors": 0,
    "last_error": "None",
    "proxies_loaded": 0
}

# Sources that provide raw text proxy lists
PROXY_SOURCES = [
    "https://spys.one/en/http-proxy-list/",
    "https://free-proxy-list.net/en/anonymous-proxy.html",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite&protocols=socks5&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=elite&limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://proxylist.geonode.com/api/proxy-list?anonymityLevel=anonymous&limit=500&page=1&sort_by=lastChecked&sort_type=desc"
]

def scrape_proxies():
    """Aggregates proxies from multiple open-source repositories."""
    combined_proxies = []
    print("[*] Scaping fresh proxies from 5 sources...")
    
    for url in PROXY_SOURCES:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Use regex to find anything that looks like an IP:Port
                found = re.findall(r'\d+\.\d+\.\d+\.\d+:\d+', response.text)
                combined_proxies.extend(found)
        except:
            continue
            
    # Remove duplicates
    unique_proxies = list(set(combined_proxies))
    print(f"[+] Total unique proxies found: {len(unique_proxies)}")
    return unique_proxies

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
    
    threading.Thread(target=manage_execution, args=(url, total)).start()
    return jsonify({"ok": True})

def send_single_request(url, proxies_list):
    """Execution logic with specific error trapping for 403s."""
    if not proxies_list:
        return False, "No Proxies"

    proxy_str = random.choice(proxies_list)
    proxies = {"http": f"http://{proxy_str}", "https": f"http://{proxy_str}"}
    
    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    try:
        # allow_redirects is critical for tracking views
        resp = requests.get(url, headers=headers, proxies=proxies, timeout=10, allow_redirects=True)
        if resp.status_code == 200:
            return True, None
        return False, f"Error {resp.status_code}"
    except Exception as e:
        return False, "Connection Failed"

def manage_execution(url, total):
    global status
    status.update({"sent": 0, "errors": 0, "running": True, "last_error": "None"})
    
    # Scrape fresh proxies right before starting
    proxies_list = scrape_proxies()
    status["proxies_loaded"] = len(proxies_list)

    if not proxies_list:
        status["running"] = False
        status["last_error"] = "Could not scrape any proxies"
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(send_single_request, url, proxies_list) for _ in range(total)]
        
        for future in concurrent.futures.as_completed(futures):
            success, err = future.result()
            if success:
                status["sent"] += 1
            else:
                status["errors"] += 1
                status["last_error"] = err
            
            # Tiny jitter to look human
            time.sleep(random.uniform(0.01, 0.03))

    status["running"] = False

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

