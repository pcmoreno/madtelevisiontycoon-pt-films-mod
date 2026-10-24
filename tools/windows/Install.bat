@echo off
rem Pacote Portugues - double-click to install. You can also drop the game folder onto this file,
rem or run "Install.bat -DryRun" from a command prompt to see what it would do.
setlocal
if not exist "%~dp0install.ps1" goto notextracted
if not exist "%~dp0data\images" goto notextracted
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
set RC=%ERRORLEVEL%
echo.
pause
exit /b %RC%
:notextracted
echo Extract the whole zip into a folder first (right-click the zip, "Extract All..."),
echo then double-click Install.bat inside the extracted folder.
pause
exit /b 1
