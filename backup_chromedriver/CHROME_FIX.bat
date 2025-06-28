@echo off
title Chrome 드라이버 문제 해결
echo ======================================
echo    Chrome 드라이버 자동 해결 도구
echo ======================================
echo.
echo 이 도구는 다음 작업을 수행합니다:
echo 1. 기존 ChromeDriver 파일 삭제
echo 2. 캐시 정리
echo 3. 패키지 업데이트
echo 4. Chrome 드라이버 테스트
echo.
echo 시작하려면 아무 키나 누르세요...
pause >nul

python C:\poison_final\fix_chromedriver_issue.py

echo.
echo ======================================
echo 작업 완료!
echo ======================================
pause
