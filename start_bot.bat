@echo off
echo === K-Fashion 자동 입찰 봇 시작 ===
echo.
cd /d %~dp0
python telegram_bot.py
pause
