# -*- coding: utf-8 -*-
"""
Claude Usage - Taskbar strip
============================
Compact, ALWAYS VISIBLE mini-bar docked at the bottom right (on the taskbar),
in the style of a stock ticker indicator like "ITX -1.05%". Shows your Claude
Code limit usage:

    C  5h 6%  ·  7d 75%

- Green <50%, yellow 50-79%, red >=80%.
- Right click: menu (Refresh / Exit).
- Hover to see the details (resets).

Data: official Claude endpoint (the same one /usage uses), with the OAuth token
from ~/.claude/.credentials.json. Nothing is sent to third parties.

Run without a console:  pythonw claude_bar.py
"""

import os
import json
import math
import socket
import sys
import threading
import urllib.request
import urllib.error
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import tkinter as tk

# ===================== Settings =====================
CRED_PATH = os.path.join(os.path.expanduser("~"), ".claude", ".credentials.json")
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
REFRESH_SECONDS = 60           # don't go below 60 (rate limit)

def _data_dir():
    """Folder for logs/position: next to the script, or in %APPDATA% when compiled."""
    if getattr(sys, "frozen", False):
        d = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ClaudeBar")
        os.makedirs(d, exist_ok=True)
        return d
    return os.path.dirname(os.path.abspath(__file__))


POS_FILE = os.path.join(_data_dir(), ".bar_pos")

# Gap on the right, inside the taskbar, before the clock/tray.
# Raise it if it overlaps another tray widget (e.g. a stock ticker);
# lower it to ~10 if you want it right next to the clock.
RIGHT_MARGIN = 180

# Colors (dark taskbar tone)
LOGO_COLOR = "#d97757"     # Claude orange
TRANSP_KEY = "#0a0b0d"     # key color: becomes transparent (taskbar shows through)
BG       = "#1b1d21"
FG       = "#e8eef5"
GRAY     = "#8a93a0"
GREEN    = "#3fb37f"
AMBER    = "#f2a93b"
RED      = "#e0533d"
FONT     = "Segoe UI"

HEIGHT = 36        # strip height (similar to the taskbar)
MIN_WIDTH = 120    # minimum width
PAD = 14           # inner left/right padding


# ===================== Data =====================
def read_token():
    try:
        with open(CRED_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    return (data.get("claudeAiOauth", {}) or {}).get("accessToken")


def fetch_usage():
    token = read_token()
    if not token:
        return {"_error": "No token (sign in to Claude Code)"}
    req = urllib.request.Request(
        USAGE_URL,
        headers={
            "Authorization": "Bearer " + token,
            "anthropic-beta": "oauth-2025-04-20",
            "User-Agent": "claude-code/2.0.0",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"_error": "Token expired (open Claude Code)"}
        if e.code == 429:
            return {"_error": "Rate limit (wait 1-2 min)"}
        return {"_error": "HTTP " + str(e.code)}
    except urllib.error.URLError:
        return {"_error": "No connection"}
    except Exception as e:
        return {"_error": str(e)[:40]}


def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def fmt_reset(iso_str):
    dt = parse_iso(iso_str)
    if dt is None:
        return ""
    sec = int((dt - datetime.now(timezone.utc)).total_seconds())
    if sec <= 0:
        return "now"
    d, rem = divmod(sec, 86400)
    h, m = rem // 3600, (rem % 3600) // 60
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


def color_pct(p):
    if p >= 80:
        return RED
    if p >= 50:
        return AMBER
    return GREEN


# ===================== Windows API prototypes =====================
_winapi_ready = False
_GetWindowLong = None
_SetWindowLong = None


def _setup_winapi():
    """Declares the correct restype/argtypes (key on 64-bit: HWNDs are
    pointers, not 32-bit ints)."""
    global _winapi_ready, _GetWindowLong, _SetWindowLong
    if _winapi_ready:
        return
    u = ctypes.windll.user32
    HWND = wintypes.HWND
    u.FindWindowW.restype = HWND
    u.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    u.FindWindowExW.restype = HWND
    u.FindWindowExW.argtypes = [HWND, HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
    u.SetParent.restype = HWND
    u.SetParent.argtypes = [HWND, HWND]
    u.GetWindowRect.restype = wintypes.BOOL
    u.GetWindowRect.argtypes = [HWND, ctypes.POINTER(wintypes.RECT)]
    u.MoveWindow.restype = wintypes.BOOL
    u.MoveWindow.argtypes = [HWND, ctypes.c_int, ctypes.c_int,
                             ctypes.c_int, ctypes.c_int, wintypes.BOOL]
    get_ = getattr(u, "GetWindowLongPtrW", None) or u.GetWindowLongW
    set_ = getattr(u, "SetWindowLongPtrW", None) or u.SetWindowLongW
    get_.restype = ctypes.c_ssize_t
    get_.argtypes = [HWND, ctypes.c_int]
    set_.restype = ctypes.c_ssize_t
    set_.argtypes = [HWND, ctypes.c_int, ctypes.c_ssize_t]
    _GetWindowLong = get_
    _SetWindowLong = set_
    _winapi_ready = True


# ===================== Widget =====================
class Bar:
    def __init__(self, root):
        self.root = root
        self.usage = None
        self.error = None
        self.loading = False
        self.remaining = 0

        # Docking state inside the taskbar
        self.docked = False
        self._hwnd = None
        self._shell = None
        self._wtitle = "ClaudeBar_%d" % os.getpid()

        root.overrideredirect(True)
        root.configure(bg=TRANSP_KEY)
        root.title(self._wtitle)
        root.geometry(f"{MIN_WIDTH}x{HEIGHT}+0+0")
        # Transparent background: the taskbar shows through
        try:
            root.attributes("-transparentcolor", TRANSP_KEY)
        except tk.TclError:
            pass

        self.canvas = tk.Canvas(root, height=HEIGHT, bg=TRANSP_KEY,
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Context menu (right click) and tooltip (on hover)
        self.canvas.bind("<Button-3>", self._menu)
        self.tip = None
        self.canvas.bind("<Enter>", self._show_tip)
        self.canvas.bind("<Leave>", self._hide_tip)

        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="Refresh now", command=self.refresh)
        self.menu.add_separator()
        self.menu.add_command(label="Exit", command=root.destroy)

        # Embed into the taskbar once the window has been created
        self.root.after(300, self._dock_to_taskbar)
        self.refresh()
        self.tick()

    # ================= TASKBAR DOCKING =================
    def _dock_to_taskbar(self):
        """Makes the window a child of the taskbar (Shell_TrayWnd), so it
        becomes part of the taskbar instead of floating."""
        try:
            _setup_winapi()
            u = ctypes.windll.user32
            self.root.update_idletasks()
            hwnd = u.FindWindowW(None, self._wtitle)
            shell = u.FindWindowW("Shell_TrayWnd", None)
            if not hwnd or not shell:
                raise RuntimeError("window or taskbar not found")

            GWL_STYLE = -16
            WS_CHILD = 0x40000000
            WS_POPUP = 0x80000000
            st = _GetWindowLong(hwnd, GWL_STYLE)
            new = (int(st) | WS_CHILD) & ~WS_POPUP & 0xFFFFFFFF
            _SetWindowLong(hwnd, GWL_STYLE, new)
            u.SetParent(hwnd, shell)

            self._hwnd = hwnd
            self._shell = shell
            self.docked = True
            self._position_in_taskbar()
        except Exception as e:
            _log_error("dock: " + repr(e))
            # Fallback: if it can't be docked, stay visible above the taskbar
            self.docked = False
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
            self._default_pos()
        self.redraw()

    def _position_in_taskbar(self):
        """Places the strip just to the left of the clock/tray area."""
        if not self.docked or not self._hwnd:
            return
        try:
            u = ctypes.windll.user32
            taskbar = wintypes.RECT()
            u.GetWindowRect(self._shell, ctypes.byref(taskbar))
            bh = taskbar.bottom - taskbar.top
            w = self._current_width()

            tray = u.FindWindowExW(self._shell, None, "TrayNotifyWnd", None)
            if tray:
                tr = wintypes.RECT()
                u.GetWindowRect(tray, ctypes.byref(tr))
                x = (tr.left - taskbar.left) - w - RIGHT_MARGIN
            else:
                x = (taskbar.right - taskbar.left) - w - RIGHT_MARGIN - 40
            y = max(0, (bh - HEIGHT) // 2)
            u.MoveWindow(self._hwnd, int(x), int(y), int(w), HEIGHT, True)
        except Exception as e:
            _log_error("position: " + repr(e))

    # ---- position ----
    def _current_width(self):
        return max(120, int(self.canvas["width"] or 180))

    def _default_pos(self):
        self.root.update_idletasks()
        w = self._current_width()
        # Actual work area (excludes the taskbar) via Windows API
        try:
            rect = wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
            right, bottom = rect.right, rect.bottom
        except Exception:
            right = self.root.winfo_screenwidth()
            bottom = self.root.winfo_screenheight() - 48
        x = right - w - 16        # flush to the right
        y = bottom - HEIGHT - 4   # just above the taskbar
        self.root.geometry(f"+{x}+{y}")
        self.root.update_idletasks()
        self._save_pos(x, y)      # save the computed coords, not winfo (not mapped yet)

    def _restore_pos(self):
        try:
            with open(POS_FILE) as f:
                x, y = map(int, f.read().split(","))
            if x <= 0 and y <= 0:   # invalid position (0,0): use the default one
                raise ValueError
            self.root.geometry(f"+{x}+{y}")
        except Exception:
            self._default_pos()

    def _save_pos(self, x=None, y=None):
        try:
            if x is None:
                x, y = self.root.winfo_x(), self.root.winfo_y()
            with open(POS_FILE, "w") as f:
                f.write(f"{int(x)},{int(y)}")
        except Exception:
            pass

    def _start_drag(self, e):
        self._dx, self._dy = e.x, e.y

    def _drag(self, e):
        x = self.root.winfo_x() + e.x - self._dx
        y = self.root.winfo_y() + e.y - self._dy
        self.root.geometry(f"+{x}+{y}")

    def _menu(self, e):
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu.grab_release()

    # ---- detail tooltip ----
    def _show_tip(self, e):
        if not self.usage:
            return
        fh = self.usage.get("five_hour") or {}
        sd = self.usage.get("seven_day") or {}
        txt = (
            f"Session 5h: {round(fh.get('utilization', 0))}%  (reset {fmt_reset(fh.get('resets_at'))})\n"
            f"Weekly 7d:  {round(sd.get('utilization', 0))}%  (reset {fmt_reset(sd.get('resets_at'))})"
        )
        self.tip = tk.Toplevel(self.root)
        self.tip.overrideredirect(True)
        self.tip.attributes("-topmost", True)
        self.tip.configure(bg="#0c2138")
        tk.Label(self.tip, text=txt, bg="#0c2138", fg=FG, justify="left",
                 font=(FONT, 9), padx=10, pady=6).pack()
        self.tip.update_idletasks()
        x = self.root.winfo_rootx()
        y = self.root.winfo_rooty() - self.tip.winfo_height() - 6
        self.tip.geometry(f"+{x}+{y}")

    def _hide_tip(self, e):
        if self.tip:
            self.tip.destroy()
            self.tip = None

    # ---- data ----
    def refresh(self):
        if self.loading:
            return
        self.loading = True

        def worker():
            r = fetch_usage()
            self.root.after(0, lambda: self._on_data(r))

        threading.Thread(target=worker, daemon=True).start()

    def _on_data(self, r):
        self.loading = False
        if "_error" in r:
            self.error = r["_error"]
        else:
            self.usage = r
            self.error = None
        self.remaining = REFRESH_SECONDS
        self.redraw()

    # ---- drawing ----
    def _icon(self, c, x, cy, color):
        """Draws the Claude logo (or a fallback circle) and returns the x
        where the text continues."""
        # Vector logo (no PNG): no halo or colored border around it
        S = 22
        mx, my = x + S / 2, cy
        lengths = [1.0, 0.72, 0.9, 0.72] * 3
        for i in range(12):
            ang = math.radians(i * 30 - 90)
            r0 = S * 0.06
            r1 = S * 0.47 * lengths[i]
            c.create_line(mx + r0 * math.cos(ang), my + r0 * math.sin(ang),
                          mx + r1 * math.cos(ang), my + r1 * math.sin(ang),
                          fill=LOGO_COLOR, width=2, capstyle="round")
        rc = S * 0.1
        c.create_oval(mx - rc, my - rc, mx + rc, my + rc,
                      fill=LOGO_COLOR, outline=LOGO_COLOR)
        return x + S + 6

    def redraw(self):
        c = self.canvas
        cy = HEIGHT / 2
        c.delete("all")
        x = PAD

        if self.usage is None:
            x = self._icon(c, x, cy, GRAY)
            msg = self.error or "loading..."
            t = c.create_text(x, cy, text="Claude  " + msg, anchor="w",
                              fill=GRAY, font=(FONT, 10))
            self._set_width(c.bbox(t)[2] + PAD)
            return

        fh = self.usage.get("five_hour") or {}
        sd = self.usage.get("seven_day") or {}
        fhp = round(fh.get("utilization", 0) or 0)
        sdp = round(sd.get("utilization", 0) or 0)

        # Claude logo
        x = self._icon(c, x, cy, color_pct(max(fhp, sdp)))

        # Stacked bars (5h on top, 7d below)
        BAR_W, BAR_H = 90, 6
        TRACK = "#3a3d42"
        rows = [("5h", fhp, cy - 8), ("7d", sdp, cy + 8)]
        x_lbl = x
        lbl_w = 0
        for lbl, _, yy in rows:
            t = c.create_text(x_lbl, yy, text=lbl, anchor="w", fill=GRAY,
                              font=(FONT, 9))
            lbl_w = max(lbl_w, c.bbox(t)[2] - x_lbl)
        x_bar = x_lbl + lbl_w + 6
        x_pct = x_bar + BAR_W + 8
        x_end = x_pct
        for lbl, pct, yy in rows:
            # Rectangles with integer coordinates: crisp on Windows
            # (thick lines with round caps come out misshapen)
            x0 = int(x_bar)
            y0 = int(round(yy - BAR_H / 2))
            c.create_rectangle(x0, y0, x0 + BAR_W, y0 + BAR_H,
                               fill=TRACK, outline="", width=0)
            p_ = max(0, min(pct, 100))
            fill_w = int(round(BAR_W * p_ / 100))
            if p_ > 0:
                fill_w = max(2, fill_w)
                c.create_rectangle(x0, y0, x0 + fill_w, y0 + BAR_H,
                                   fill=color_pct(pct), outline="", width=0)
            t = c.create_text(x_pct, yy, text=f"{pct}%", anchor="w", fill=FG,
                              font=(FONT, 9, "bold"))
            x_end = max(x_end, c.bbox(t)[2])
        x = x_end

        if self.error:   # stale data, but the last request failed
            t = c.create_text(x + 8, cy, text="⚠", anchor="w", fill=AMBER,
                              font=(FONT, 11))
            x = c.bbox(t)[2]

        self._set_width(x + PAD)

    def _set_width(self, w):
        w = max(MIN_WIDTH, int(w))
        if abs(w - int(self.canvas["width"] or 0)) > 2:
            self.canvas.config(width=w)
            self.root.geometry(f"{w}x{HEIGHT}")
            if self.docked:
                self._position_in_taskbar()

    # ---- clock ----
    def tick(self):
        if self.remaining > 0:
            self.remaining -= 1
        if self.remaining <= 0 and not self.loading:
            self.refresh()
        # Re-assert the position inside the taskbar every 5s (in case the tray changes)
        if self.docked:
            self._dock_tick = getattr(self, "_dock_tick", 0) + 1
            if self._dock_tick % 5 == 0:
                self._position_in_taskbar()
        self.root.after(1000, self.tick)


def _log_error(msg):
    try:
        p = os.path.join(_data_dir(), "bar_error.log")
        with open(p, "a", encoding="utf-8") as f:
            f.write(datetime.now().isoformat() + "  " + msg + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    # Single instance (avoids duplicates and requests that trigger the 429)
    _lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _lock.bind(("127.0.0.1", 50574))
    except OSError:
        _log_error("another instance is already running (port 50574 in use); exiting")
        sys.exit(0)

    try:
        root = tk.Tk()
        root.title("Claude Bar")
        Bar(root)
        root.mainloop()
    except Exception as e:
        import traceback
        _log_error("CRASH: " + repr(e) + "\n" + traceback.format_exc())
        raise
