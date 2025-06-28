@echo off
echo === Chrome 드라이버 버전 문제 해결 ===
echo.
echo 1. Chrome 브라우저와 ChromeDriver 버전 확인
echo.
python C:\poison_final\check_chrome_version.py
echo.
echo ====================================
echo.
echo 2. 그래도 안되면 다음 명령 실행:
echo.
echo pip install --upgrade selenium
echo pip install --upgrade undetected-chromedriver
echo pip install --upgrade webdriver-manager
echo.
pause
