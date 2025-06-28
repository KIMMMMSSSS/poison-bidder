#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABC마트 링크 추출기 디버그 및 셀렉터 업데이트
"""

import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

def debug_and_fix_selectors():
    """ABC마트 셀렉터 문제 디버그"""
    driver = None
    try:
        # Chrome 옵션 설정
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Chrome 바이너리 경로 설정
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]
        
        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                options.binary_location = chrome_path
                break
        
        print("Chrome 드라이버 초기화...")
        driver_path = "C:/poison_final/chromedriver.exe"
        if os.path.exists(driver_path):
            driver = uc.Chrome(
                options=options,
                driver_executable_path=driver_path,
                version_main=None
            )
        else:
            driver = uc.Chrome(options=options)
        
        # ABC마트 아디다스신발 검색
        url = "https://abcmart.a-rt.com/display/search-word/result?searchWord=아디다스신발"
        print(f"\n페이지 접속: {url}")
        driver.get(url)
        time.sleep(5)  # 페이지 로딩 대기
        
        # JavaScript로 현재 페이지의 실제 상품 링크 구조 파악
        js_result = driver.execute_script("""
            // 모든 a 태그 찾기
            var allLinks = document.querySelectorAll('a[href]');
            var productLinks = [];
            var selectors = {};
            
            // prdtNo를 포함하는 링크 찾기
            for (var i = 0; i < allLinks.length; i++) {
                var href = allLinks[i].href;
                if (href && href.includes('prdtNo=')) {
                    productLinks.push(href);
                    
                    // 이 링크의 클래스명과 부모 클래스 수집
                    var elem = allLinks[i];
                    var elemClasses = elem.className;
                    if (elemClasses) {
                        selectors['a.' + elemClasses.split(' ').join('.')] = 1;
                    }
                    
                    // 부모 요소의 클래스도 확인
                    var parent = elem.parentElement;
                    while (parent && parent.tagName !== 'BODY') {
                        if (parent.className) {
                            var parentSelector = parent.tagName.toLowerCase() + '.' + parent.className.split(' ').join('.');
                            selectors[parentSelector + ' a[href*="prdtNo"]'] = 1;
                        }
                        parent = parent.parentElement;
                    }
                }
            }
            
            return {
                productCount: productLinks.length,
                sampleLinks: productLinks.slice(0, 5),
                possibleSelectors: Object.keys(selectors).slice(0, 10)
            };
        """)
        
        print(f"\n[결과]")
        print(f"발견된 상품 링크: {js_result['productCount']}개")
        
        if js_result['productCount'] > 0:
            print("\n샘플 링크:")
            for i, link in enumerate(js_result['sampleLinks'], 1):
                print(f"{i}. {link}")
            
            print("\n가능한 셀렉터:")
            for selector in js_result['possibleSelectors']:
                print(f"- {selector}")
            
            # 더 간단한 셀렉터로 테스트
            simple_selectors = [
                'a[href*="prdtNo="]',  # 가장 기본적인 셀렉터
                'a[href*="/product?prdtNo="]',
                '[href*="prdtNo="]'
            ]
            
            print("\n[간단한 셀렉터 테스트]")
            for selector in simple_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"[OK] '{selector}': {len(elements)}개 발견")
                except Exception as e:
                    print(f"[FAIL] '{selector}': {e}")
            
        else:
            print("\n[문제] 상품 링크를 찾을 수 없습니다!")
            print("'아디다스신발'로 검색 결과가 없을 수 있습니다.")
            print("'아디다스'로 다시 시도합니다...")
            
            # 아디다스로 재시도
            url2 = "https://abcmart.a-rt.com/display/search-word/result?searchWord=아디다스"
            driver.get(url2)
            time.sleep(5)
            
            # 다시 테스트
            elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="prdtNo="]')
            print(f"\n'아디다스' 검색 결과: {len(elements)}개 링크 발견")
        
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()
            print("\n브라우저 종료")


if __name__ == "__main__":
    debug_and_fix_selectors()
