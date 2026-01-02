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

status = {
    "running": False,
    "sent": 0,
    "total": 0,
    "errors": 0,
    "last_error": "None"
}

def load_proxies_from_url():
    """Fetches proxies and reports if the link itself is broken."""
    try:
        print(f"[*] Fetching proxy list from: {PROXY_LIST_URL}")
        response = requests.get(PROXY_LIST_URL, timeout=15)
        if response.status_code == 200:
            proxies = [line.strip() for line in response.text.splitlines() if line.strip()]
            print(f"[+] Successfully loaded {len(proxies)} proxies.")
            return proxies
        else:
            status["last_error"] = f"Proxy Link Error: Status {response.status_code}"
            return []
    except Exception as e:
        status["last_error"] = f"Failed to reach Proxy Link: {str(e)}"
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

    thread = threading.Thread(target=manage_execution, args=(url, total))
    thread.start()
    return jsonify({"ok": True})

def send_single_request(url, proxies_list):
    """Sends request and captures specific error messages."""
    if not proxies_list:
        return False, "No proxies available"

    proxy_str = random.choice(proxies_list)
    proxies = {"http": proxy_str, "https": proxy_str}
    
    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/"
    }

    try:
        # We MUST use allow_redirects for links to count
        response = requests.get(url, headers=headers, proxies=proxies, timeout=12, allow_redirects=True)
        
        if response.status_code == 200:
            return True, None
        else:
            return False, f"Server returned {response.status_code}"
    except requests.exceptions.ProxyError:
        return False, "Proxy Refused Connection"
    except requests.exceptions.Timeout:
        return False, "Proxy Timed Out"
    except Exception as e:
        return False, str(e)

def manage_execution(url, total):
    global status
    status["sent"] = 0
    status["errors"] = 0
    status["running"] = True
    
    proxies_list = load_proxies_from_url()
    
    if not proxies_list:
        status["running"] = False
        print("[!] Execution stopped: No proxies found.")
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_single_request, url, proxies_list) for _ in range(total)]
        
        for future in concurrent.futures.as_completed(futures):
            success, error_msg = future.result()
            if success:
                status["sent"] += 1
            else:
                status["errors"] += 1
                status["last_error"] = error_msg
                print(f"[X] Request Failed: {error_msg}")
            
            time.sleep(random.uniform(0.01, 0.05))

    status["running"] = False
    print("--- Task Finished ---")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)