===========================================================
  CLAUDE USAGE  -  Mac version (menu bar, with SwiftBar)
===========================================================

Shows your Claude Code usage at the top right, next to the clock:

      ✳  5h ▬▬▬▬▬▬ 3%
         7d ▬▬▬▬▬▬ 16%

   - 5h  = session window   ·   7d = weekly window
   - Colors: green <50%, yellow 50-79%, red >=80%
   - Click -> details with the reset times and "Refresh now"
   - Adapts to macOS light / dark mode
   - Refreshes every minute (the "1m" in the file name)

-----------------------------------------------------------
 INSTALL
-----------------------------------------------------------
  1) Copy this "mac" folder to the Mac.
  2) Open Terminal in the folder and run:

        bash install.sh

     Installs SwiftBar (with Homebrew) and Pillow if missing,
     copies the plugin to ~/SwiftBarPlugins and opens SwiftBar.
  3) If macOS asks for Keychain access ("Claude Code-credentials"),
     click "Always Allow".
  4) Start at login: SwiftBar > Preferences > Launch at login.

-----------------------------------------------------------
 UPDATE
-----------------------------------------------------------
  Run "bash install.sh" again after changing the plugin.

-----------------------------------------------------------
 TROUBLESHOOTING
-----------------------------------------------------------
  "No token":       open Claude Code and check you're signed in.
                    The token is looked up in the Keychain
                    (service "Claude Code-credentials") and,
                    failing that, in ~/.claude/.credentials.json.
  "Token expired":  open Claude Code for a moment; it renews itself.
  Text only (✳ 3% · 16%) instead of bars: Pillow is missing ->
                    /usr/bin/python3 -m pip install --user pillow
  Test by hand:     python3 ~/SwiftBarPlugins/claude_usage.1m.py
===========================================================
