@echo off
REM Removes the automatic start with Windows.
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Claude Bar.lnk" 2>nul
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Claude Barra.lnk" 2>nul
echo.
echo  Autostart DISABLED.
echo.
pause
