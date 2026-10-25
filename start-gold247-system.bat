@echo off
title GOLD24-7 + OpenTraderWorld Autonomous System Launcher
echo ======================================================================
echo   GOLD24-7 Research Engine + XM MT5 + OpenTraderWorld Journal
echo ======================================================================
echo.

echo [1/4] Ensuring OpenTraderWorld Docker Stack is running in WSL2...
wsl.exe -d Ubuntu -u vall bash -c "cd /home/vall/m-2nd-brain/code/opentraderworld/deploy && docker compose up -d"

echo [2/4] Checking Ollama daemon (Hermes 3:8B on GPU)...
wsl.exe -d Ubuntu -u vall bash -c "systemctl is-active --quiet ollama || sudo systemctl start ollama"

echo [3/4] Ensuring XM MT5 Bridge is running on port 8082...
powershell -NoProfile -Command "if (-not (Get-NetTCPConnection -LocalPort 8082 -State Listen -ErrorAction SilentlyContinue)) { Write-Host '  Starting MT5 Bridge Server on Windows (Port 8082)...' -ForegroundColor Cyan; Start-Process 'C:\Users\Legion\AppData\Local\Programs\Python\Python313\python.exe' -ArgumentList '\\wsl.localhost\Ubuntu\home\vall\m-2nd-brain\code\gold24-7\scripts\mt5_bridge_server.py' -WindowStyle Hidden; Start-Sleep -Seconds 2 } else { Write-Host '  [OK] MT5 Bridge is active on port 8082.' -ForegroundColor Green }"

echo [4/4] Starting GOLD24-7 Research Dashboard (Port 8585)...
start /b wsl.exe -d Ubuntu -u vall bash -c "cd $HOME/dev/gold24-7 && source .venv/bin/activate && python -m uvicorn dashboard.server:app --host 0.0.0.0 --port 8585"

echo.
echo Launching Web Interfaces:
echo   - OpenTraderWorld Journal: http://localhost:5454
echo   - GOLD24-7 Live Research Dashboard: http://localhost:8585
start http://localhost:5454
start http://localhost:8585

echo.
echo ======================================================================
echo   Stack Operational!
echo   To launch continuous autonomous trading daemon in WSL2:
echo     wsl.exe -d Ubuntu -u vall bash -c "cd $HOME/dev/gold24-7 && source .venv/bin/activate && python scripts/daemon_runner.py"
echo ======================================================================
timeout /t 5 >nul
