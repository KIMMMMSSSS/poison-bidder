@echo off
echo 기존 봇 프로세스 종료 중...
taskkill /F /IM python.exe 2>nul
timeout /t 2 >nul

echo.
echo K-Fashion 자동 입찰 봇 시작...
echo.
python telegram_bot.py
pause
