import instaloader
import tkinter as tk
from tkinter import messagebox
from urllib.parse import urlparse

def extract_username(url_or_name):
    if "instagram.com" in url_or_name:
        return urlparse(url_or_name).path.strip("/").split("/")[0]
    return url_or_name

def download():
    username = extract_username(entry.get())

    try:
        L = instaloader.Instaloader()
        profile = instaloader.Profile.from_username(L.context, username)
        L.download_profile(profile)
        messagebox.showinfo("Done", f"Downloaded {username}")
    except Exception as e:
        messagebox.showerror("Error", str(e))

root = tk.Tk()
root.title("Instagram Fetcher")
root.geometry("350x150")

tk.Label(root, text="Profile URL or username").pack(pady=5)

entry = tk.Entry(root, width=40)
entry.pack(pady=5)

tk.Button(root, text="Download", command=download).pack(pady=10)

root.mainloop()
