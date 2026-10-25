@echo off
title MT5 Daily Journal Auto-Sync Watchdog
color 0A
echo ====================================================================
echo           MT5 TO OPENTRADERWORLD DAILY SURE-SYNC WATCHDOG
echo ====================================================================
echo  This service monitors MetaTrader 5 on your Windows machine.
echo  When you close or log out of MT5 at the end of your session,
echo  it automatically synchronizes all closed trades, PnL, fees, and
echo  brackets directly into your OpenTraderWorld Trading Journal.
echo ====================================================================
echo.

cd /d "%~dp0\.."
wsl -d Ubuntu bash -c "cd $HOME/dev/gold24-7 && .venv/bin/python scripts/auto_sync_daily_history.py --watch-logout"

pause
