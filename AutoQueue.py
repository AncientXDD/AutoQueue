import time
import requests
import base64
import urllib3
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
from tkinter import ttk
import sv_ttk  

# Optional: apply dark title bar on Windows
import sys
try:
    import pywinstyles 
except ImportError:
    pywinstyles = None

# ─── CONFIG ────────────────────────────────────────────────────────────────────
LOCKFILE_PATH  = r"C:\Riot Games\League of Legends\lockfile"
#QUEUE_ID       = 420       # e.g. 420 = Ranked Solo/Duo
REQUEUE_DELAY  = 1         # seconds between cancel + next queue
HTTP_TIMEOUT   = 10        # seconds before an HTTP call to the client times out
# ────────────────────────────────────────────────────────────────────────────────

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

running = False
thread = None

def read_lockfile(path):
    name, pid, port, pwd, proto = open(path).read().split(":")
    return port, pwd

def make_session(port, pwd):
    token = base64.b64encode(f"riot:{pwd}".encode()).decode()
    sess = requests.Session()
    sess.verify = False
    sess.headers.update({
        "Authorization": f"Basic {token}",
        "Accept":        "application/json",
    })
    return sess, f"https://127.0.0.1:{port}"

def log(msg):
    text_area.configure(state='normal')
    text_area.insert(tk.END, msg + "\n")
    text_area.see(tk.END)
    text_area.configure(state='disabled')

def queue_loop(wait_secs):
    global running
    try:
        port, pwd = read_lockfile(LOCKFILE_PATH)
    except Exception as e:
        messagebox.showerror("Error", f"Lockfile error: {e}")
        return
    sess, base = make_session(port, pwd)

    log(f"⏱️  Loop: {wait_secs}s wait")
    while running:
        try:
            r = sess.post(f"{base}/lol-lobby/v2/lobby/matchmaking/search", timeout=HTTP_TIMEOUT)
            if r.status_code != 204:
                log("🛑Not in Lobby")
                stop()     
                return      

            log(f"➡️  Queued")
        except Exception as e:
            log(f"⚠️  Queue failed: {e}")
            break

        for _ in range(int(wait_secs)):
            if not running: break
            time.sleep(1)
        if not running: break

        try:
            r = sess.delete(f"{base}/lol-lobby/v2/lobby/matchmaking/search", timeout=HTTP_TIMEOUT)
            log(f"🛑  Canceled")
        except Exception as e:
            log(f"⚠️  Cancel failed: {e}")
            break

        for _ in range(int(REQUEUE_DELAY)):
            if not running: break
            time.sleep(1)

    # Cleanup: if loop ended
    try:
        r = sess.delete(f"{base}/lol-lobby/v2/lobby/matchmaking/search", timeout=HTTP_TIMEOUT)
        log(f"🛑  Canceled")
    except Exception:
        pass
    log("👋 Queue loop stopped")

def start():
    global running, thread
    if running:
        return
    try:
        m = int(min_entry.get())
        s = int(sec_entry.get())
        if m < 0 or s < 0 or s >= 60:
            raise ValueError
    except ValueError:
        messagebox.showerror("Input error", "Minutes ≥ 0, seconds 0–59")
        return

    wait_secs = m * 60 + s
    running = True
    start_btn['state'] = 'disabled'
    stop_btn['state'] = 'normal'
    thread = threading.Thread(target=queue_loop, args=(wait_secs,), daemon=True)
    thread.start()

def stop():
    global running
    running = False
    stop_btn['state'] = 'disabled'
    start_btn['state'] = 'normal'

def apply_titlebar(root):
    if not pywinstyles:
        return
    ver = sys.getwindowsversion()
    if ver.major == 10 and ver.build >= 22000:
        col = "#1c1c1c"
        pywinstyles.change_header_color(root, col)
    elif ver.major == 10:
        pywinstyles.apply_style(root, 'dark')
        root.wm_attributes('-alpha', 0.99)
        root.wm_attributes('-alpha', 1)

root = tk.Tk()
root.title("AncientXDD")

sv_ttk.set_theme("dark")
apply_titlebar(root)

style = ttk.Style()
bg = style.lookup('TFrame', 'background') or '#1c1c1c'
entry_bg = style.lookup('TEntry', 'fieldbackground') or bg
entry_fg = style.lookup('TEntry', 'foreground') or '#ffffff'

root.configure(bg=bg)

frm = ttk.Frame(root, padding=10)
frm.pack(fill='both', expand=True)

# Minutes input
ttk.Label(frm, text="Minutes:").grid(row=0, column=0, sticky='e')
min_entry = ttk.Entry(frm, width=5)
min_entry.insert(0, '2')
min_entry.grid(row=0, column=1, padx=(0,10))

# Seconds input
ttk.Label(frm, text="Seconds:").grid(row=0, column=2, sticky='e')
sec_entry = ttk.Entry(frm, width=5)
sec_entry.insert(0, '0')
sec_entry.grid(row=0, column=3, padx=(0,10))

# Buttons
bfrm = ttk.Frame(frm)
bfrm.grid(row=1, column=0, columnspan=6, pady=10)
start_btn = ttk.Button(bfrm, text='Start', command=start)
start_btn.pack(side='left', padx=5)
stop_btn = ttk.Button(bfrm, text='Stop', state='disabled', command=stop)
stop_btn.pack(side='left', padx=5)

# Log area
text_area = scrolledtext.ScrolledText(
    frm,
    width=35,
    height=10,
    state='disabled',
    bg=entry_bg,
    fg=entry_fg,
    insertbackground=entry_fg
)
text_area.grid(row=2, column=0, columnspan=6)

root.mainloop()
