@echo off
chcp 65001 >nul
cd /d "%~dp0"
taskkill /f /im headless.exe >nul 2>&1
del /q "%~dp0x64dbg\release\x64\headless\db\ZBrush.exe.dd64" 2>nul

for /f %%i in ('powershell -NoProfile -Command "$p=Get-Process ZBrush -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1; if(-not $p){$p=Get-Process ZBrush -ErrorAction SilentlyContinue | Sort-Object StartTime -Descending | Select-Object -First 1}; $p.Id"') do set PID=%%i
if "%PID%"=="" (
  echo [X] ZBrush is not running. Start ZBrush first, then run this again.
  pause
  exit /b
)

echo [*] Attaching to ZBrush (PID %PID%) ...
echo [*] When attached, rotate on the EMPTY canvas with LEFT button for 3-5 seconds.
cd /d "%~dp0x64dbg\release\x64"
powershell -NoProfile -Command "Start-Process -FilePath (Join-Path (Get-Location) 'headless.exe') -ArgumentList @('-a','%PID%','-cf','capture_rotate.txt') -WorkingDirectory (Get-Location) -RedirectStandardOutput (Join-Path (Get-Location) 'capture_headless.log') -RedirectStandardError (Join-Path (Get-Location) 'capture_headless_err.log') -NoNewWindow; Start-Sleep -Seconds 40; Get-Process headless -ErrorAction SilentlyContinue | Stop-Process -Force"

echo.
echo [*] ===== Result =====
findstr /C:"NLC_" capture_headless.log
echo [*] ===================
pause
