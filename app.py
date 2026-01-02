import os
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello, world! Your app is running."

@app.route("/status")
def status():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    # Always bind to the port the cloud platform gives you
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
