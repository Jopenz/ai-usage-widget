# -*- coding: utf-8 -*-
"""
Claude Bar installer (a single .exe)
====================================
Installs the widget in %LOCALAPPDATA%\\ClaudeBar, adds it to Windows startup,
creates a Start menu shortcut and registers it in "Apps & features" so it can
be uninstalled. Does not need admin rights.

    ClaudeBar-Setup.exe               install
    ClaudeBar-Setup.exe --uninstall   uninstall
"""

import os
import sys
import shutil
import subprocess
import winreg
import tkinter as tk
from tkinter import messagebox

NAME = "Claude Bar"
WIDGET_EXE = "ClaudeBar.exe"
SETUP_EXE = "ClaudeBar-Setup.exe"
REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\ClaudeBar"
NO_WINDOW = 0x08000000   # CREATE_NO_WINDOW

TARGET = os.path.join(os.environ["LOCALAPPDATA"], "ClaudeBar")
STARTUP = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
START_MENU = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs")
STARTUP_LNK = os.path.join(STARTUP, NAME + ".lnk")
MENU_LNK = os.path.join(START_MENU, NAME + ".lnk")
DATA_DIR = os.path.join(os.environ["APPDATA"], "ClaudeBar")

# Previous install under the old Spanish name ("Claude Barra"), removed on install
LEGACY_EXE = "ClaudeBarra.exe"
LEGACY_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\ClaudeBarra"
LEGACY_DIRS = (os.path.join(os.environ["LOCALAPPDATA"], "ClaudeBarra"),
               os.path.join(os.environ["APPDATA"], "ClaudeBarra"))
LEGACY_LNKS = (os.path.join(STARTUP, "Claude Barra.lnk"),
               os.path.join(START_MENU, "Claude Barra.lnk"))


def resource(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def create_shortcut(lnk, target, workdir):
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');"
          "$s.TargetPath='%s';$s.WorkingDirectory='%s';$s.Save()" % (lnk, target, workdir))
    subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                   creationflags=NO_WINDOW, check=True)


def close_widget(exe=WIDGET_EXE):
    subprocess.run(["taskkill", "/F", "/IM", exe],
                   creationflags=NO_WINDOW,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def remove_files(paths):
    for f in paths:
        try:
            os.remove(f)
        except OSError:
            pass


def delete_reg_key(key):
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
    except OSError:
        pass


def remove_legacy():
    close_widget(LEGACY_EXE)
    remove_files(LEGACY_LNKS)
    delete_reg_key(LEGACY_REG_KEY)
    for d in LEGACY_DIRS:
        shutil.rmtree(d, ignore_errors=True)


def install():
    close_widget()
    remove_legacy()
    os.makedirs(TARGET, exist_ok=True)
    target_exe = os.path.join(TARGET, WIDGET_EXE)
    target_setup = os.path.join(TARGET, SETUP_EXE)
    shutil.copyfile(resource(WIDGET_EXE), target_exe)
    shutil.copyfile(sys.executable, target_setup)   # so it can be uninstalled

    create_shortcut(STARTUP_LNK, target_exe, TARGET)
    create_shortcut(MENU_LNK, target_exe, TARGET)

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY) as k:
        winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, NAME)
        winreg.SetValueEx(k, "DisplayVersion", 0, winreg.REG_SZ, "1.2")
        winreg.SetValueEx(k, "Publisher", 0, winreg.REG_SZ, "Claude Bar")
        winreg.SetValueEx(k, "InstallLocation", 0, winreg.REG_SZ, TARGET)
        winreg.SetValueEx(k, "DisplayIcon", 0, winreg.REG_SZ, target_exe)
        winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ,
                          '"%s" --uninstall' % target_setup)
        winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)

    subprocess.Popen([target_exe], cwd=TARGET, creationflags=NO_WINDOW)


def uninstall():
    close_widget()
    remove_files((STARTUP_LNK, MENU_LNK))
    delete_reg_key(REG_KEY)
    # Delete the folder after exiting (this .exe lives inside it)
    subprocess.Popen('cmd /c ping 127.0.0.1 -n 3 >nul & rmdir /s /q "%s"' % TARGET,
                     shell=True, creationflags=NO_WINDOW)
    shutil.rmtree(DATA_DIR, ignore_errors=True)


def main():
    root = tk.Tk()
    root.withdraw()
    try:
        if "--uninstall" in sys.argv:
            if messagebox.askyesno(NAME, "Uninstall %s?" % NAME):
                uninstall()
                messagebox.showinfo(NAME, "%s has been uninstalled." % NAME)
        else:
            if messagebox.askyesno(
                    NAME,
                    "%s will be installed for your user and will start with Windows.\n\n"
                    "It shows your Claude Code usage inside the taskbar.\n\n"
                    "Install now?" % NAME):
                install()
                messagebox.showinfo(NAME, "Installed. The widget is now on the taskbar.")
    except Exception as e:
        messagebox.showerror(NAME, "Error: %s" % e)
    root.destroy()


if __name__ == "__main__":
    main()
