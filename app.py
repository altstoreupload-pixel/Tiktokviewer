from flask import Flask, render_template, request, jsonify
import time
import threading

app = Flask(__name__)

# Shared variable to track progress
progress_data = {
    "running": False,
    "progress": 0,
    "target": 0
}

def send_views(video_url, target_views):
    """Simulate sending views to your website"""
    progress_data["running"] = True
    progress_data["progress"] = 0
    progress_data["target"] = target_views
    
    for i in range(1, target_views + 1):
        time.sleep(0.1)  # simulate sending a view
        progress_data["progress"] = i
    
    progress_data["running"] = False

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/start', methods=['POST'])
def start():
    data = request.json
    video_url = data.get("video_url")
    target_views = int(data.get("target_views", 0))
    
    if progress_data["running"]:
        return jsonify({"status": "running"})
    
    thread = threading.Thread(target=send_views, args=(video_url, target_views))
    thread.start()
    return jsonify({"status": "started"})

@app.route('/progress')
def progress():
    return jsonify(progress_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
