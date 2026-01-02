from flask import Flask, request, jsonify
import time
from threading import Thread

app = Flask(__name__)

# Dictionary to store progress per task
tasks_progress = {}

def send_views(task_id, video_url, total_views):
    """Simulate sending views in background."""
    sent = 0
    while sent < total_views:
        time.sleep(1)  # simulate network delay
        sent += 1
        tasks_progress[task_id] = sent
    tasks_progress[task_id] = total_views  # mark as done

@app.route('/')
def index():
    return '''
    <h1>Viewer Bot Simulator</h1>
    <form action="/start" method="post">
      Video URL: <input type="text" name="video_url"><br>
      Number of Views: <input type="number" name="views"><br>
      <input type="submit" value="Start" id="startBtn">
    </form>
    <div id="progress"></div>
    <script>
      const form = document.querySelector('form');
      const progressDiv = document.getElementById('progress');
      const startBtn = document.getElementById('startBtn');

      form.addEventListener('submit', async e => {
        e.preventDefault();
        startBtn.disabled = true;
        startBtn.style.backgroundColor = 'grey';
        const video_url = form.video_url.value;
        const views = form.views.value;
        const res = await fetch('/start', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({video_url, views})
        });
        const data = await res.json();
        const task_id = data.task_id;

        const interval = setInterval(async () => {
          const progRes = await fetch('/progress/' + task_id);
          const progData = await progRes.json();
          progressDiv.innerHTML = `Progress: ${progData.sent}/${views}`;
          if (progData.sent >= views) {
            clearInterval(interval);
            startBtn.disabled = false;
            startBtn.style.backgroundColor = 'green';
          }
        }, 500);
      });
    </script>
    '''

@app.route('/start', methods=['POST'])
def start_task():
    data = request.get_json()
    video_url = data.get('video_url')
    views = int(data.get('views', 0))
    task_id = str(time.time()).replace('.', '')
    tasks_progress[task_id] = 0

    # Start background thread
    thread = Thread(target=send_views, args=(task_id, video_url, views))
    thread.start()
    return jsonify({'task_id': task_id})

@app.route('/progress/<task_id>')
def progress(task_id):
    sent = tasks_progress.get(task_id, 0)
    return jsonify({'sent': sent})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
