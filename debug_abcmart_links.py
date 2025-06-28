#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABC마트 링크 추출 디버그 스크립트
현재 페이지 구조를 분석하여 올바른 셀렉터를 찾습니다.
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from datetime import datetime

# 콘솔 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def debug_abcmart_links():
    """ABC마트 링크 추출 디버그"""
    print("=" * 60)
    print("ABC마트 링크 추출 디버그")
    print("=" * 60)
    
    driver = None
    try:
        # Chrome 옵션 설정
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        # headless 모드 비활성화 (디버그를 위해)
        # options.add_argument("--headless")
        
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
        
        print("\n1. Chrome 드라이버 초기화...")
        driver = uc.Chrome(options=options)
        print("[OK] 드라이버 초기화 성공")
        
        # ABC마트 아디다스 검색 페이지
        url = "https://abcmart.a-rt.com/display/search-word/result?searchWord=아디다스&page=1"
        
        print(f"\n2. 페이지 접속: {url}")
        driver.get(url)
        time.sleep(5)  # 페이지 로딩 대기
        
        print("\n3. 페이지 구조 분석...")
        
        # 모든 링크 수집
        all_links = driver.find_elements(By.TAG_NAME, 'a')
        print(f"   - 전체 링크 수: {len(all_links)}개")
        
        # 상품 링크 필터링
        product_links = []
        for link in all_links:
            href = link.get_attribute('href')
            if href and 'prdtNo=' in href:
                product_links.append(href)
        
        print(f"   - prdtNo 포함 링크: {len(product_links)}개")
        
        if product_links:
            print("\n4. 샘플 상품 링크 (처음 5개):")
            for i, link in enumerate(product_links[:5], 1):
                print(f"   {i}. {link}")
        
        # 다양한 셀렉터 테스트
        print("\n5. CSS 셀렉터 테스트:")
        selectors = [
            'a[href*="product?prdtNo="]',
            'a[href*="prdtNo="]',
            '.item-list a[href]',
            '.search-list-wrap a[href]',
            '.item_area a[href]',
            '.list_item a[href]',
            '.product-list a[href*="prdtNo"]',
            '[class*="product"] a[href*="prdtNo"]',
            # 추가 셀렉터 시도
            'div[class*="item"] a[href*="prdtNo"]',
            'li[class*="item"] a[href*="prdtNo"]',
            '[class*="prd"] a[href*="prdtNo"]',
            '[class*="goods"] a[href*="prdtNo"]',
            'ul li a[href*="prdtNo"]',
            # 더 일반적인 셀렉터
            'a[href*="/product?"]',
            'a[href*="/product/"]'
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"   [OK] '{selector}': {len(elements)}개 발견")
                    # 첫 번째 요소의 부모 클래스 확인
                    if elements:
                        parent_classes = elements[0].find_element(By.XPATH, '..').get_attribute('class')
                        print(f"      부모 클래스: {parent_classes}")
            except Exception as e:
                print(f"   [FAIL] '{selector}': 오류 - {e}")
        
        # JavaScript로 상품 링크 찾기
        print("\n6. JavaScript로 링크 패턴 분석:")
        js_result = driver.execute_script("""
            // 모든 링크 수집
            var links = document.querySelectorAll('a[href]');
            var productLinks = [];
            var patterns = {};
            
            for (var i = 0; i < links.length; i++) {
                var href = links[i].href;
                if (href && href.includes('prdtNo=')) {
                    productLinks.push(href);
                    
                    // 부모 요소들의 클래스 수집
                    var parent = links[i].parentElement;
                    while (parent && parent.tagName !== 'BODY') {
                        if (parent.className) {
                            var classes = parent.className.split(' ');
                            for (var j = 0; j < classes.length; j++) {
                                var cls = classes[j].trim();
                                if (cls && cls.length > 2) {
                                    patterns[cls] = (patterns[cls] || 0) + 1;
                                }
                            }
                        }
                        parent = parent.parentElement;
                    }
                }
            }
            
            // 가장 많이 나타나는 클래스 패턴 정렬
            var sortedPatterns = Object.entries(patterns)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10);
            
            return {
                totalLinks: links.length,
                productCount: productLinks.length,
                sampleLinks: productLinks.slice(0, 3),
                commonClasses: sortedPatterns
            };
        """)
        
        print(f"   - JavaScript로 찾은 상품 링크: {js_result['productCount']}개")
        print(f"   - 샘플 링크:")
        for i, link in enumerate(js_result['sampleLinks'], 1):
            print(f"     {i}. {link}")
        
        print(f"\n   - 자주 나타나는 클래스 패턴:")
        for cls, count in js_result['commonClasses']:
            print(f"     * {cls}: {count}회")
        
        # 페이지 소스 일부 저장
        print("\n7. 페이지 소스 저장...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 전체 페이지 저장
        with open(f'abcmart_debug_full_{timestamp}.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print(f"   - 전체 페이지: abcmart_debug_full_{timestamp}.html")
        
        # 상품 영역만 저장 (있다면)
        try:
            product_area = driver.find_element(By.CSS_SELECTOR, '[class*="list"], [class*="item"], [class*="product"]')
            with open(f'abcmart_debug_products_{timestamp}.html', 'w', encoding='utf-8') as f:
                f.write(product_area.get_attribute('outerHTML'))
            print(f"   - 상품 영역: abcmart_debug_products_{timestamp}.html")
        except:
            print("   - 상품 영역을 찾을 수 없습니다.")
        
        # 추천 셀렉터 생성
        if product_links:
            print("\n8. 추천 셀렉터:")
            # 실제로 작동하는 셀렉터 찾기
            working_selectors = []
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) >= len(product_links) * 0.8:  # 80% 이상 찾으면 유효
                        working_selectors.append((selector, len(elements)))
                except:
                    pass
            
            if working_selectors:
                working_selectors.sort(key=lambda x: x[1], reverse=True)
                print("   작동하는 셀렉터:")
                for selector, count in working_selectors[:3]:
                    print(f"   • {selector} ({count}개)")
            else:
                print("   [WARNING] 적절한 셀렉터를 찾지 못했습니다. 페이지 구조가 변경되었을 수 있습니다.")
        
        print("\n✅ 디버그 완료!")
        
    except Exception as e:
        print("\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            input("\n엔터를 눌러 브라우저를 닫고 종료하세요...")
            driver.quit()


if __name__ == "__main__":
    debug_abcmart_links()
