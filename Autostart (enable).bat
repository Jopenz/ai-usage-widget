@echo off
REM Creates a shortcut in the Windows Startup folder so the Claude strip
REM starts on its own when the computer boots (no console window).
set "SCRIPT=%~dp0claude_bar.py"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
del "%STARTUP%\Claude Barra.lnk" 2>nul
powershell -NoProfile -Command "$w=New-Object -ComObject WScript.Shell; $l=$w.CreateShortcut(Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\Claude Bar.lnk'); $p=(Get-Command pythonw.exe).Source; $l.TargetPath=$p; $l.Arguments='\"%SCRIPT%\"'; $l.WorkingDirectory='%~dp0'; $l.WindowStyle=7; $l.Save()"
echo.
echo  Autostart ENABLED. The strip will start with Windows.
echo.
pause
