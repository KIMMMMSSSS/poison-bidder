#!/usr/bin/env python3
"""ABC마트 검색 테스트"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

def test_abcmart_search():
    """ABC마트 검색 테스트"""
    print("ABC마트 검색 테스트 시작...")
    
    # 드라이버 설정
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    driver = uc.Chrome(options=options, version_main=None)
    
    try:
        # 검색 URL
        keyword = "뉴발란스"
        search_url = f"https://abcmart.a-rt.com/display/search-word/result?ntab&smartSearchCheck=false&perPage=30&sort=point&dfltChnnlMv=&searchPageGubun=product&track=W0010&searchWord={keyword}&page=1&channel=10001&chnnlNo=10001&tabGubun=total"
        
        print(f"URL: {search_url}")
        driver.get(search_url)
        
        print("페이지 로드 대기 중...")
        time.sleep(5)
        
        # 현재 URL 확인
        print(f"현재 URL: {driver.current_url}")
        
        # 페이지 제목 확인
        print(f"페이지 제목: {driver.title}")
        
        # 상품 링크 찾기
        print("\n상품 링크 검색 중...")
        
        # 다양한 셀렉터 시도
        selectors = [
            "a[href*='/product/detail/']",
            "a[href*='prdtCode=']",
            ".product-item a",
            ".item-box a",
            "a.product-link"
        ]
        
        found_links = []
        for selector in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"셀렉터 '{selector}'로 {len(elements)}개 요소 발견")
                for elem in elements[:3]:  # 처음 3개만
                    href = elem.get_attribute('href')
                    if href:
                        print(f"  - {href}")
                        found_links.append(href)
        
        if not found_links:
            print("상품 링크를 찾지 못했습니다.")
            
            # 페이지 소스 일부 출력
            print("\n페이지 HTML 일부:")
            body = driver.find_element(By.TAG_NAME, "body")
            print(body.get_attribute('innerHTML')[:1000])
        
        input("\nEnter를 눌러 종료...")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    test_abcmart_search()
