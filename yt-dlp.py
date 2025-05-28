import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import requests
import subprocess
import platform  # Import platform for opening folder

# Constants
APP_DATA_DIR = Path.home() / ".my_yt_downloader"
YT_DLP_PATH = APP_DATA_DIR / "yt-dlp.exe"
YT_DLP_LATEST_RELEASE_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
YT_DLP_DOWNLOAD_URL_TEMPLATE = "https://github.com/yt-dlp/yt-dlp/releases/download/{tag}/yt-dlp.exe"

# Ensure app data directory exists
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Helper to run subprocesses without console
def run_subprocess_without_console(args):
    kwargs = {
        'stdout': subprocess.PIPE,
        'stderr': subprocess.STDOUT,
        'text': True
    }
    if sys.platform == "win32":
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(args, **kwargs)

def is_ffmpeg_installed():
    result = run_subprocess_without_console(["ffmpeg", "-version"])
    return result.returncode == 0

def update_status(text):
    progress_label.config(text=text)
    progress_label.update_idletasks()

def download_yt_dlp_binary():
    update_status("Fetching latest yt-dlp release info...")
    try:
        resp = requests.get(YT_DLP_LATEST_RELEASE_API, timeout=10)
        resp.raise_for_status()
        tag_name = resp.json()["tag_name"]
        download_url = YT_DLP_DOWNLOAD_URL_TEMPLATE.format(tag=tag_name)
        
        update_status(f"Downloading yt-dlp {tag_name}...")
        with requests.get(download_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(YT_DLP_PATH, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        try:
            os.chmod(YT_DLP_PATH, 0o755)  # Make executable
        except Exception:
            pass
        update_status(f"yt-dlp {tag_name} downloaded successfully!")
    except Exception as e:
        update_status(f"Failed to download yt-dlp: {e}")
        messagebox.showerror("Error", f"Failed to download yt-dlp:\n{e}")

def check_dependencies():
    if not is_ffmpeg_installed():
        messagebox.showwarning(
            "Missing Dependency",
            "FFmpeg is not installed or not in your system PATH.\n\n"
            "Some video/audio conversions may fail without it.\n\n"
            "You can download it from: https://ffmpeg.org/download.html"
        )
        
def ensure_yt_dlp():
    if not YT_DLP_PATH.exists():
        threading.Thread(target=download_yt_dlp_binary, daemon=True).start()
    else:
        update_status("")

def open_downloads_folder():
    """Open the user's Downloads folder in the system file explorer"""
    downloads_path = Path.home() / "Downloads"
    try:
        if platform.system() == "Windows":
            os.startfile(str(downloads_path))
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", str(downloads_path)])
        else:  # Linux and others
            subprocess.run(["xdg-open", str(downloads_path)])
    except Exception as e:
        messagebox.showerror("Error", f"Could not open Downloads folder: {e}")

def download_video():
    # Hide the open button at start of new download
    if open_button.winfo_ismapped():
        open_button.pack_forget()
    
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Error", "Please enter a YouTube URL.")
        return
    if not YT_DLP_PATH.exists():
        messagebox.showerror("Error", "yt-dlp binary is missing. Please update yt-dlp first.")
        return

    download_button.config(state='disabled')
    update_status("Starting download...")

    def run_download():
        is_mp3 = mp3_var.get()
        downloads_path = str(Path.home() / "Downloads")
        cmd = [str(YT_DLP_PATH), url, "--no-mtime", "-o", os.path.join(downloads_path, "%(title)s.%(ext)s")]

        if is_mp3:
            cmd += ["-x", "--audio-format", "mp3", "--audio-quality", "192K"]
        else:
            cmd += [
                "-f", "bv*[height<=1080]+ba/bestvideo+bestaudio",
                "--merge-output-format", "mp4",
                "--postprocessor-args", "-c:a aac -b:a 192k"
            ]

        # Suppress console for subprocess
        kwargs = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.STDOUT,
            'text': True
        }
        if sys.platform == "win32":
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

        process = subprocess.Popen(cmd, **kwargs)

        for line in process.stdout:
            update_status(line.strip())
        process.wait()

        if process.returncode == 0:
            update_status("Download completed successfully!")
            # Show the open button after successful download
            open_button.pack(pady=5)
        else:
            update_status("Download failed. See console for details.")
            messagebox.showerror("Error", "Download failed. Check console output.")
        download_button.config(state='normal')

    threading.Thread(target=run_download, daemon=True).start()

def update_yt_dlp():
    update_button.config(state='disabled')
    update_status("Updating yt-dlp...")
    def run_update():
        download_yt_dlp_binary()
        yt_dlp_version_var.set(f"YouTube Downloader (yt-dlp v{get_yt_dlp_version()})")
        update_button.config(state='normal')
    threading.Thread(target=run_update, daemon=True).start()

def get_yt_dlp_version():
    result = run_subprocess_without_console([str(YT_DLP_PATH), "--version"])
    return result.stdout.strip() if result.returncode == 0 else "unknown"

# GUI setup
root = tk.Tk()
try:
    icon_path = resource_path("icon.ico")
    root.iconbitmap(icon_path)
except Exception as e:
    print(f"Error setting icon: {e}")

root.title("YouTube Downloader")
root.geometry("550x355")  # Increased height to accommodate new button
root.resizable(False, False)
root.configure(bg="#f3f4f6")

style = ttk.Style()
style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
style.configure("TEntry", font=("Segoe UI", 10))
style.configure("TLabel", font=("Segoe UI", 10))

yt_dlp_version_var = tk.StringVar()
yt_dlp_version_var.set(f"YouTube Downloader (yt-dlp v{get_yt_dlp_version()})")

version_label = ttk.Label(root, textvariable=yt_dlp_version_var, font=("Segoe UI", 15, "bold"))
version_label.pack(pady=(30, 10))

url_entry = ttk.Entry(root, width=50)
url_entry.pack(pady=5)

mp3_var = tk.BooleanVar()
ttk.Checkbutton(root, text="Download as MP3 (audio only)", variable=mp3_var).pack(pady=(5, 10))

download_button = ttk.Button(root, text="Start Download", command=download_video)
download_button.pack(pady=5)

update_button = ttk.Button(root, text="Update yt-dlp", command=update_yt_dlp)
update_button.pack(pady=5)

progress_label = ttk.Label(root, text="", foreground="#1f2937")
progress_label.pack(pady=10)

# Create the "Open Downloads Folder" button but don't show it initially
open_button = ttk.Button(
    root, 
    text="📂 Open Downloads Folder", 
    command=open_downloads_folder
)

credits_label = ttk.Label(
    root,
    text="© 2025 Khairon Gonzales — Made with yt-dlp for Puting Kahoy SDA Church",
    font=("Segoe UI", 9),
    foreground="#727884"
)
credits_label.pack(side="bottom", pady=(10, 5))

ensure_yt_dlp()
check_dependencies()
root.mainloop()