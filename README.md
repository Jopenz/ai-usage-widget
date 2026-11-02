# AI Usage Widget

Shows your **Claude Code** plan usage (5-hour session and 7-day weekly limits) at a glance:

- **Windows** – a compact strip docked inside the taskbar, next to the clock/tray.
- **macOS** – a menu bar item via [SwiftBar](https://swiftbar.app).

```
✳  5h ███░░░░░ 19%
   7d ██████░░ 77%
```

- `5h` = session window (resets every 5 hours) · `7d` = weekly window
- Colors: green < 50%, yellow 50–79%, red ≥ 80%
- Hover (Windows) or click (macOS) for the time left until each reset

## How it works

The widget calls the same endpoint Claude Code's `/usage` uses
(`api.anthropic.com/api/oauth/usage`) with your local Claude Code OAuth token:

- Windows: `~/.claude/.credentials.json`
- macOS: the Keychain (`Claude Code-credentials`), falling back to `~/.claude/.credentials.json`

Nothing is sent anywhere else. You need Claude Code installed and signed in.

## Windows

Requires Python 3 (with tkinter, included in the standard installer).

| File | Purpose |
|---|---|
| `claude_bar.py` | The widget |
| `Start widget.bat` | Launches it without a console window |
| `Autostart (enable).bat` / `Autostart (disable).bat` | Start it (or stop starting it) with Windows |
| `Build installer.bat` | Builds `output\ClaudeBar-Setup.exe` with PyInstaller |

Quick start: double-click `Start widget.bat`, then `Autostart (enable).bat` once.

The installer (`ClaudeBar-Setup.exe`) needs no admin rights: it installs to
`%LOCALAPPDATA%\ClaudeBar`, adds a Start menu entry and autostart, and registers an
uninstaller under *Apps & features*.

Settings at the top of `claude_bar.py`:

- `RIGHT_MARGIN` (default `180`) – gap from the clock/tray. Raise it if it overlaps
  another tray widget, lower it to ~10 to sit next to the clock.
- `REFRESH_SECONDS` (default `60`) – polling interval. Don't go below 60 (API rate limit).

## macOS

```bash
cd mac
bash install.sh
```

Installs SwiftBar (via Homebrew) and Pillow if missing, copies the plugin to
`~/SwiftBarPlugins` and opens SwiftBar. Allow Keychain access to
`Claude Code-credentials` when asked. See [mac/README.txt](mac/README.txt) for details.

## Troubleshooting

- **"No token"** – open Claude Code and make sure you're signed in.
- **"Token expired"** – open Claude Code for a moment; it renews the token and the widget recovers on its own.
- **"Rate limit"** – wait 1–2 minutes.
