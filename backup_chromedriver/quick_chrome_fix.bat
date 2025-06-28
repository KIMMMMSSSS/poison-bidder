@echo off
echo === Chrome 드라이버 빠른 해결 ===
echo.

REM 1. 기존 파일 삭제
echo [1] 기존 ChromeDriver 삭제 중...
del /f /q chromedriver.exe 2>nul
del /f /q chromedriver_backup.exe 2>nul
del /f /q chromedriver_old.zip 2>nul
echo    완료!

REM 2. 캐시 삭제
echo.
echo [2] 캐시 삭제 중...
rmdir /s /q "%APPDATA%\undetected_chromedriver" 2>nul
rmdir /s /q "%LOCALAPPDATA%\undetected_chromedriver" 2>nul
rmdir /s /q "%USERPROFILE%\.undetected_chromedriver" 2>nul
echo    완료!

REM 3. 패키지 업데이트
echo.
echo [3] 패키지 업데이트 중...
pip install --upgrade selenium webdriver-manager undetected-chromedriver
echo    완료!

echo.
echo ======================================
echo ✅ Chrome 드라이버 문제 해결 완료!
echo ======================================
echo.
echo 이제 다음 명령을 실행하세요:
echo python unified_bidding.py --site abcmart --web-scraping --search-keyword "아디다스신발"
echo.
pause
