import tkinter as tk
from tkinter import messagebox
from downloader import InstagramDownloader
from urllib.parse import urlparse
import threading


def extract_username(text):
    if "instagram.com" in text:
        return urlparse(text).path.strip("/").split("/")[0]
    return text


def run_download():
    username = extract_username(entry.get())

    def task():
        try:
            status.set("Downloading...")
            d = InstagramDownloader(max_workers=6)
            d.download_profile(username)
            status.set("Complete!")
            messagebox.showinfo("Done", "Finished downloading.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            status.set("Failed")

    threading.Thread(target=task).start()


root = tk.Tk()
root.title("Instagram Fetcher")
root.geometry("400x180")

tk.Label(root, text="Instagram username or URL").pack(pady=8)

entry = tk.Entry(root, width=45)
entry.pack()

tk.Button(root, text="Download", command=run_download).pack(pady=10)

status = tk.StringVar(value="Idle")
tk.Label(root, textvariable=status).pack()

root.mainloop()
