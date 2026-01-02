import os
import random
import threading
import time
from flask import Flask, render_template, request, jsonify
from curl_cffi import requests

app = Flask(__name__)

# Global Stats Tracking
stats = {
    "sent": 0,
    "total": 0,
    "errors": 0,
    "proxies_loaded": 0,
    "running": False,
    "finished": False
}

def get_random_proxy():
    """Efficiently picks one proxy from the file without loading everything into RAM."""
    if not os.path.exists("proxies.txt"):
        return None
    try:
        with open("proxies.txt", "r") as f:
            lines = f.readlines()
            if not lines: return None
            return random.choice(lines).strip()
    except Exception as e:
        print(f"Read Error: {e}")
        return None

def worker_logic(target_url, total_views):
    """Main execution thread for handling views via proxies."""
    global stats
    
    # Update total proxy count for the UI
    if os.path.exists("proxies.txt"):
        with open("proxies.txt", "r") as f:
            stats["proxies_loaded"] = sum(1 for _ in f)

    # Real-world referral sources to mimic organic traffic
    referrers = [
        "https://www.google.com/", "https://www.tiktok.com/", 
        "https://t.co/", "https://www.facebook.com/"
    ]

    # Use a thread pool or simple loop based on target volume
    for _ in range(total_views):
        if not stats["running"]: break
            
        success = False
        retries = 0
        
        while not success and retries < 2: # Try up to 2 different proxies per view
            p_raw = get_random_proxy()
            if not p_raw: break
                
            proxies = {"http": f"http://{p_raw}", "https": f"http://{p_raw}"}
            headers = {
                "Referer": random.choice(referrers),
                "Accept-Language": "en-US,en;q=0.9"
            }
            
            try:
                # impersonate="chrome110" handles the TLS fingerprint bypass
                resp = requests.get(
                    target_url, 
                    headers=headers,
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
        
        # Micro-sleep to prevent CPU spiking on Koyeb
        time.sleep(0.05)

    stats["running"] = False
    stats["finished"] = True

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    data = request.json
    if stats["running"]:
        return jsonify({"ok": False, "error": "Already running"})
    
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
    # Koyeb requires binding to 0.0.0.0
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
