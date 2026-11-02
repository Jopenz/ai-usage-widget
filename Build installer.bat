@echo off
REM Builds ClaudeBar.exe and the ClaudeBar-Setup.exe installer ("output" folder).
cd /d "%~dp0"

python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 python -m pip install pyinstaller
if errorlevel 1 ( echo [ERROR] Could not install PyInstaller & pause & exit /b 1 )

echo [1/2] Building the widget...
python -m PyInstaller --noconfirm --onefile --noconsole --name ClaudeBar claude_bar.py
if errorlevel 1 ( echo [ERROR] Failed to build the widget & pause & exit /b 1 )

echo [2/2] Building the installer...
python -m PyInstaller --noconfirm --onefile --noconsole --name ClaudeBar-Setup ^
    --add-data "dist\ClaudeBar.exe;." installer.py
if errorlevel 1 ( echo [ERROR] Failed to build the installer & pause & exit /b 1 )

if not exist output mkdir output
copy /Y "dist\ClaudeBar-Setup.exe" "output\ClaudeBar-Setup.exe" >nul
copy /Y "dist\ClaudeBar.exe" "output\ClaudeBar.exe" >nul
rmdir /S /Q build dist __pycache__ >nul 2>&1
del /Q *.spec >nul 2>&1

echo.
echo DONE: output\ClaudeBar-Setup.exe
pause
