@echo off
echo ========================================
echo 텔레그램 봇 안전 실행
echo ========================================
echo.
echo 기존 봇 프로세스를 확인하고 종료합니다...
taskkill /f /im python.exe 2>NUL
echo.
echo 3초 대기...
timeout /t 3 /nobreak >NUL
echo.
echo 봇을 시작합니다...
python telegram_bot.py
pause
