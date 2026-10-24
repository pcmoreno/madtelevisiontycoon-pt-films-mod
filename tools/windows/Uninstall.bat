@echo off
rem Pacote Portugues - double-click to remove the mod. You can also drop the game folder onto this file,
rem or run "Uninstall.bat -DryRun" from a command prompt to see what it would do.
setlocal
if not exist "%~dp0uninstall.ps1" goto notextracted
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1" %*
set RC=%ERRORLEVEL%
echo.
pause
exit /b %RC%
:notextracted
echo Extract the whole zip into a folder first (right-click the zip, "Extract All..."),
echo then double-click Uninstall.bat inside the extracted folder.
pause
exit /b 1
