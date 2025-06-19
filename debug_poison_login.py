#!/usr/bin/env python3
"""
포이즌 사이트 로그인 디버그
실제 로그인 요소를 찾기 위한 스크립트
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

def debug_poison_login():
    """포이즌 사이트 로그인 요소 디버그"""
    print("\n" + "="*50)
    print("POIZON 사이트 로그인 디버그")
    print("="*50)
    
    # 드라이버 초기화
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    driver = uc.Chrome(options=options, version_main=None)
    
    try:
        # 로그인 페이지로 이동
        print("\n1. 로그인 페이지 접속 중...")
        driver.get("https://seller.poizon.com/login")
        time.sleep(3)
        
        print("\n2. 페이지 요소 분석 중...")
        
        # 가능한 ID 필드 찾기
        print("\n[ID 입력 필드 찾기]")
        id_selectors = [
            "input[name='username']",
            "input[name='email']",
            "input[name='account']",
            "input[name='phone']",
            "input[type='text']",
            "input[placeholder*='账号']",
            "input[placeholder*='用户']",
            "input[placeholder*='邮箱']",
            "input[placeholder*='手机']"
        ]
        
        for selector in id_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for elem in elements:
                        print(f"✓ 찾음: {selector}")
                        print(f"  - name: {elem.get_attribute('name')}")
                        print(f"  - placeholder: {elem.get_attribute('placeholder')}")
                        print(f"  - type: {elem.get_attribute('type')}")
            except:
                pass
        
        # 가능한 비밀번호 필드 찾기
        print("\n[비밀번호 입력 필드 찾기]")
        pw_selectors = [
            "input[type='password']",
            "input[name='password']",
            "input[placeholder*='密码']"
        ]
        
        for selector in pw_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for elem in elements:
                        print(f"✓ 찾음: {selector}")
                        print(f"  - name: {elem.get_attribute('name')}")
                        print(f"  - placeholder: {elem.get_attribute('placeholder')}")
            except:
                pass
        
        # 가능한 로그인 버튼 찾기
        print("\n[로그인 버튼 찾기]")
        button_selectors = [
            "button[type='submit']",
            "button[type='button']",
            ".login-btn",
            ".submit-btn",
            "button",
            "input[type='submit']"
        ]
        
        for selector in button_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for elem in elements:
                        text = elem.text or elem.get_attribute('value')
                        if text:
                            print(f"✓ 찾음: {selector} - 텍스트: '{text}'")
            except:
                pass
        
        # 수동 로그인 안내
        print("\n" + "="*50)
        print("수동 로그인 테스트")
        print("="*50)
        print("1. 브라우저에서 직접 로그인해주세요.")
        print("2. 로그인 완료 후 Enter를 누르세요.")
        print("="*50)
        
        input("\n로그인 완료 후 Enter를 누르세요...")
        
        # 로그인 후 요소 찾기
        print("\n3. 로그인 후 사용자 정보 요소 찾기...")
        
        user_selectors = [
            ".user-name",
            ".user-info",
            ".username",
            ".avatar",
            ".user-avatar",
            ".account-info",
            "[class*='user']",
            "[class*='account']",
            "[class*='avatar']"
        ]
        
        found_elements = []
        for selector in user_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for elem in elements:
                        text = elem.text
                        if text:
                            print(f"✓ 찾음: {selector} - 텍스트: '{text}'")
                            found_elements.append(selector)
            except:
                pass
        
        print("\n" + "="*50)
        print("분석 완료!")
        print("="*50)
        
        if found_elements:
            print(f"\n로그인 확인 요소로 사용 가능: {found_elements[0]}")
        
        input("\n종료하려면 Enter를 누르세요...")
        
    except Exception as e:
        print(f"\n오류 발생: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    debug_poison_login()
