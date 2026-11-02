#!/usr/bin/python3
# -*- coding: utf-8 -*-
# <xbar.title>Claude Usage</xbar.title>
# <xbar.desc>Claude Code usage (5h / 7d) with stacked bars in the menu bar.</xbar.desc>
# <xbar.dependencies>python3, pillow</xbar.dependencies>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideLastUpdated>true</swiftbar.hideLastUpdated>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>
"""
Claude Usage - SwiftBar plugin (macOS)
======================================
Mac version of the Windows widget (claude_bar.py). SwiftBar runs it every
minute (the "1m" in the file name) and draws in the menu bar:

    ✳  5h ▬▬▬▬▬▬ 3%
       7d ▬▬▬▬▬▬ 16%

On click: details with the reset times and "Refresh now".

Token: first the macOS Keychain (where Claude Code stores it on Mac) and, if
it's not there, ~/.claude/.credentials.json. Nothing is sent to third parties.
If Pillow is missing, it shows text only ("✳ 3% · 16%").
"""

import base64
import io
import json
import math
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone

# ===================== Settings =====================
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
KEYCHAIN_SERVICE = "Claude Code-credentials"
CRED_PATH = os.path.expanduser("~/.claude/.credentials.json")
CACHE = os.path.expanduser("~/Library/Caches/claude-usage-swiftbar.json")

LOGO_COLOR = (217, 119, 87)      # Claude orange
GREEN = (63, 179, 127)
AMBER = (242, 169, 59)
RED = (224, 83, 61)

DARK = os.environ.get("OS_APPEARANCE", "Dark") != "Light"
if DARK:
    FG, GRAY, TRACK = (242, 242, 247), (152, 152, 157), (72, 72, 74)
else:
    FG, GRAY, TRACK = (29, 29, 31), (110, 110, 115), (199, 199, 204)

SCALE = 2         # drawn at 2x (retina) and tagged as 144 dpi
HEIGHT_PT = 22    # menu bar height
BAR_W_PT = 50
BAR_H_PT = 3.5


# ===================== Data =====================
def read_token():
    # 1) macOS Keychain
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            data = json.loads(out.stdout.strip())
            tok = (data.get("claudeAiOauth", {}) or {}).get("accessToken")
            if tok:
                return tok
    except Exception:
        pass
    # 2) File (as on Windows/Linux)
    try:
        with open(CRED_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return (data.get("claudeAiOauth", {}) or {}).get("accessToken")
    except Exception:
        return None


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


def cache_read():
    try:
        with open(CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def cache_save(d):
    try:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump({"t": datetime.now(timezone.utc).isoformat(), "usage": d}, f)
    except Exception:
        pass


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


def fmt_ago(iso_str):
    dt = parse_iso(iso_str)
    if dt is None:
        return ""
    sec = int((datetime.now(timezone.utc) - dt).total_seconds())
    if sec < 60:
        return "a few seconds ago"
    if sec < 3600:
        return f"{sec // 60} min ago"
    return f"{sec // 3600} h ago"


def color_pct(p):
    if p >= 80:
        return RED
    if p >= 50:
        return AMBER
    return GREEN


def hexc(rgb):
    return "#%02x%02x%02x" % rgb


# ===================== Image =====================
def _font(size_px, bold=False):
    from PIL import ImageFont
    candidates = [
        ("/System/Library/Fonts/SFNS.ttf", 0),
        ("/System/Library/Fonts/Helvetica.ttc", 1 if bold else 0),
        ("/Library/Fonts/Arial.ttf", 0),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
         else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0),
    ]
    for path, idx in candidates:
        if os.path.exists(path):
            try:
                f = ImageFont.truetype(path, size_px, index=idx)
                if bold and path.endswith("SFNS.ttf"):
                    try:
                        f.set_variation_by_name("Semibold")
                    except Exception:
                        pass
                return f
            except Exception:
                continue
    return ImageFont.load_default()


def bars_image(fhp, sdp, warning=False):
    """Returns the PNG (base64) with the logo + two stacked bars."""
    from PIL import Image, ImageDraw

    SS = 2                     # supersampling: smooth logo and text
    S = SCALE * SS
    height = HEIGHT_PT * S
    f_lbl = _font(int(8.5 * S))
    f_pct = _font(int(8.5 * S), bold=True)

    # Measurements
    logo = 14 * S
    x_lbl = logo + 5 * S
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    w_lbl = max(tmp.textlength(t, font=f_lbl) for t in ("5h", "7d"))
    x_bar = int(x_lbl + w_lbl + 4 * S)
    bar_w = BAR_W_PT * S
    x_pct = x_bar + bar_w + 5 * S
    w_pct = max(tmp.textlength(f"{p}%", font=f_pct) for p in (fhp, sdp))
    width = int(x_pct + w_pct + (12 * S if warning else 1 * S))
    width += width % SS

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Logo (12 rays, as on Windows)
    cx, cy = logo / 2, height / 2
    lengths = [1.0, 0.72, 0.9, 0.72] * 3
    for i in range(12):
        ang = math.radians(i * 30 - 90)
        r0, r1 = logo * 0.06, logo * 0.47 * lengths[i]
        d.line([(cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)),
                (cx + r1 * math.cos(ang), cy + r1 * math.sin(ang))],
               fill=LOGO_COLOR, width=int(1.6 * S))
    rc = logo * 0.1
    d.ellipse([cx - rc, cy - rc, cx + rc, cy + rc], fill=LOGO_COLOR)

    # Rows
    bar_h = int(BAR_H_PT * S)
    for lbl, pct, yy in (("5h", fhp, 6 * S), ("7d", sdp, 16 * S)):
        d.text((x_lbl, yy), lbl, font=f_lbl, fill=GRAY, anchor="lm")
        y0 = int(yy - bar_h / 2)
        d.rectangle([x_bar, y0, x_bar + bar_w - 1, y0 + bar_h - 1], fill=TRACK)
        p = max(0, min(pct, 100))
        if p > 0:
            w = max(2 * S, int(round(bar_w * p / 100)))
            d.rectangle([x_bar, y0, x_bar + w - 1, y0 + bar_h - 1], fill=color_pct(pct))
        d.text((x_pct, yy), f"{pct}%", font=f_pct, fill=FG, anchor="lm")

    if warning:
        d.text((width - 9 * S, height / 2), "⚠", font=f_pct, fill=AMBER, anchor="lm")

    img = img.resize((width // SS, height // SS), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG", dpi=(72 * S, 72 * S))   # 144 dpi -> correct size on retina
    return base64.b64encode(buf.getvalue()).decode("ascii")


# ===================== SwiftBar output =====================
def main():
    r = fetch_usage()
    error = r.get("_error") if isinstance(r, dict) else "Unexpected response"
    if error:
        c = cache_read()
        usage = c.get("usage") if c else None
        when = c.get("t") if c else None
    else:
        usage = r
        cache_save(r)
        when = datetime.now(timezone.utc).isoformat()

    # --- Menu bar line ---
    if usage is None:
        print(f"✳ {error} | color={hexc(GRAY)} size=12")
        print("---")
        print("Refresh now | refresh=true")
        return

    fh = usage.get("five_hour") or {}
    sd = usage.get("seven_day") or {}
    fhp = round(fh.get("utilization", 0) or 0)
    sdp = round(sd.get("utilization", 0) or 0)

    try:
        b64 = bars_image(fhp, sdp, warning=bool(error))
        print(f"| image={b64}")
    except ImportError:
        warning = " ⚠" if error else ""
        print(f"✳ {fhp}% · {sdp}%{warning} | size=12")

    # --- Dropdown menu ---
    print("---")
    print(f"Session (5h) · {fhp}% | color={hexc(color_pct(fhp))}")
    if fh.get("resets_at"):
        print(f"Resets in {fmt_reset(fh.get('resets_at'))}")
    print("---")
    print(f"Weekly (7d) · {sdp}% | color={hexc(color_pct(sdp))}")
    if sd.get("resets_at"):
        print(f"Resets in {fmt_reset(sd.get('resets_at'))}")
    print("---")
    if error:
        print(f"⚠ {error} | color={hexc(AMBER)}")
    print("Refresh now | refresh=true")
    if when:
        print(f"Updated {fmt_ago(when)} | size=11")


if __name__ == "__main__":
    main()
