import threading
import requests
import tkinter as tk
from tkinter import messagebox
import time

# ================= CONFIG =================
REQUEST_DELAY = 0.3   # seconds between requests
TIMEOUT = 10
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
# =========================================


class TrafficApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Website Traffic Sender")
        self.root.geometry("420x260")
        self.root.resizable(False, False)

        tk.Label(root, text="Target URL", font=("Arial", 12)).pack(pady=5)
        self.url_entry = tk.Entry(root, width=50)
        self.url_entry.pack()

        tk.Label(root, text="Number of Requests", font=("Arial", 12)).pack(pady=5)
        self.count_entry = tk.Entry(root, width=20)
        self.count_entry.pack()

        self.start_btn = tk.Button(
            root,
            text="START",
            bg="green",
            fg="white",
            font=("Arial", 14, "bold"),
            command=self.start
        )
        self.start_btn.pack(pady=20, ipadx=20, ipady=5)

        self.status = tk.Label(root, text="Idle", font=("Arial", 10))
        self.status.pack()

    def start(self):
        url = self.url_entry.get().strip()
        try:
            count = int(self.count_entry.get().strip())
        except:
            messagebox.showerror("Error", "Enter a valid number")
            return

        if not url.startswith("http"):
            messagebox.showerror("Error", "Enter a valid URL")
            return

        self.start_btn.config(state=tk.DISABLED, bg="gray")
        self.status.config(text="Running...")

        thread = threading.Thread(
            target=self.send_requests,
            args=(url, count),
            daemon=True
        )
        thread.start()

    def send_requests(self, url, count):
        sent = 0
        for i in range(count):
            try:
                requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                sent += 1
                self.status.config(text=f"Sent {sent}/{count}")
            except:
                pass
            time.sleep(REQUEST_DELAY)

        self.root.after(0, self.finish)

    def finish(self):
        self.status.config(text="Done")
        self.start_btn.config(state=tk.NORMAL, bg="green")


if __name__ == "__main__":
    root = tk.Tk()
    app = TrafficApp(root)
    root.mainloop()
