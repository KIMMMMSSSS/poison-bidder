#!/usr/bin/env python3
"""
ABC마트 검색 스크래퍼
검색어를 입력받아 ABC마트에서 상품을 검색하고 링크를 추출하는 스크래퍼
"""

import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from datetime import datetime
import undetected_chromedriver as uc
from urllib.parse import urlencode, quote_plus
import logging
import json
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ABCMartSearchScraper:
    """ABC마트 검색 스크래퍼"""
    
    def __init__(self, headless=False):
        self.driver = None
        self.wait = None
        self.headless = headless
        self.base_url = "https://abcmart.a-rt.com"
        
    def setup_driver(self):
        """Chrome 드라이버 설정"""
        try:
            logger.info("Chrome 드라이버 초기화 중...")
            
            options = uc.ChromeOptions()
            
            if self.headless:
                options.add_argument('--headless')
                
            # 기본 옵션
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-blink-features=AutomationControlled')
            
            # User-Agent 설정
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 로깅 최소화
            options.add_argument('--log-level=3')
            options.add_argument('--silent')
            
            # 이미지 로딩 비활성화 (속도 향상)
            prefs = {
                'profile.default_content_setting_values': {
                    'images': 2,
                    'plugins': 2,
                    'popups': 2,
                    'geolocation': 2,
                    'notifications': 2,
                    'media_stream': 2,
                }
            }
            options.add_experimental_option('prefs', prefs)
            
            # 드라이버 생성
            self.driver = uc.Chrome(options=options, version_main=None)
            self.wait = WebDriverWait(self.driver, 20)
            
            logger.info("Chrome 드라이버 초기화 완료")
            
        except Exception as e:
            logger.error(f"Chrome 드라이버 설정 실패: {e}")
            raise
            
    def search_products(self, keyword, max_pages=10):
        """ABC마트에서 상품 검색"""
        try:
            logger.info(f"ABC마트 검색 시작: '{keyword}'")
            
            # 검색 URL 생성
            search_url = f"{self.base_url}/display/search-word/result?searchWord={quote_plus(keyword)}"
            logger.info(f"검색 URL: {search_url}")
            
            # 검색 페이지로 이동
            self.driver.get(search_url)
            time.sleep(3)  # 페이지 로드 대기
            
            # 검색 결과 확인
            try:
                # 검색 결과 개수 확인
                result_count_elem = self.driver.find_element(By.CSS_SELECTOR, ".search-result-count, .total-count, [class*='count']")
                result_count_text = result_count_elem.text
                logger.info(f"검색 결과: {result_count_text}")
            except:
                logger.info("검색 결과 개수를 찾을 수 없음")
            
            # 상품 링크 수집
            all_links = []
            
            for page in range(1, max_pages + 1):
                logger.info(f"페이지 {page} 스크래핑 중...")
                
                # 페이지 URL 생성
                if page > 1:
                    page_url = f"{search_url}&page={page}"
                    self.driver.get(page_url)
                    time.sleep(2)
                
                # 상품 링크 추출
                links = self.extract_product_links()
                
                if not links:
                    logger.info(f"페이지 {page}에서 상품을 찾을 수 없음")
                    break
                    
                logger.info(f"페이지 {page}에서 {len(links)}개 상품 발견")
                all_links.extend(links)
                
                # 다음 페이지 버튼 확인
                if not self.has_next_page():
                    logger.info("마지막 페이지 도달")
                    break
                    
                # 페이지 간 대기
                time.sleep(1)
            
            # 중복 제거
            unique_links = list(set(all_links))
            logger.info(f"총 {len(unique_links)}개의 고유 상품 링크 수집")
            
            return unique_links
            
        except Exception as e:
            logger.error(f"검색 중 오류 발생: {e}")
            return []
            
    def extract_product_links(self):
        """현재 페이지에서 상품 링크 추출"""
        links = []
        
        try:
            # 다양한 선택자로 상품 링크 찾기
            selectors = [
                'a[href*="/product?prdtNo="]',
                'a[href*="/product/detail"]',
                '.product-item a[href*="prdtNo"]',
                '.item-list a[href*="product"]',
                '.search-list-wrap a[href*="product"]',
                'div[class*="product"] a[href*="prdtNo"]',
                'li[class*="product"] a[href*="prdtNo"]',
                '[data-product-no] a',
                '.prd-item a',
                '.goods-item a'
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.debug(f"선택자 '{selector}'로 {len(elements)}개 요소 발견")
                    
                    for elem in elements:
                        href = elem.get_attribute('href')
                        if href and 'prdtNo=' in href:
                            # 표준 형식으로 변환
                            match = re.search(r'prdtNo=(\d+)', href)
                            if match:
                                product_id = match.group(1)
                                standard_url = f"{self.base_url}/product?prdtNo={product_id}"
                                links.append(standard_url)
                except Exception as e:
                    logger.debug(f"선택자 '{selector}' 처리 중 오류: {e}")
                    continue
                    
            # JavaScript로 추가 시도
            if not links:
                logger.info("CSS 선택자로 찾지 못함, JavaScript로 시도")
                js_links = self.driver.execute_script("""
                    var links = [];
                    var anchors = document.querySelectorAll('a[href]');
                    
                    for (var i = 0; i < anchors.length; i++) {
                        var href = anchors[i].href;
                        if (href && href.includes('prdtNo=')) {
                            links.push(href);
                        }
                    }
                    
                    return links;
                """)
                
                for href in js_links:
                    match = re.search(r'prdtNo=(\d+)', href)
                    if match:
                        product_id = match.group(1)
                        standard_url = f"{self.base_url}/product?prdtNo={product_id}"
                        links.append(standard_url)
                        
        except Exception as e:
            logger.error(f"링크 추출 중 오류: {e}")
            
        return links
        
    def has_next_page(self):
        """다음 페이지 존재 여부 확인"""
        try:
            # 다음 페이지 버튼 찾기
            next_selectors = [
                'a.next:not(.disabled)',
                'button.next:not(:disabled)',
                '[class*="next"]:not(.disabled)',
                'a[title="다음"]',
                'button[title="다음"]'
            ]
            
            for selector in next_selectors:
                try:
                    next_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_btn.is_enabled() and next_btn.is_displayed():
                        return True
                except:
                    continue
                    
            return False
            
        except Exception:
            return False
            
    def save_results(self, links, keyword):
        """결과 저장"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON 파일로 저장
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        json_file = output_dir / f"abcmart_search_{keyword}_{timestamp}.json"
        data = {
            "site": "abcmart",
            "keyword": keyword,
            "total_count": len(links),
            "links": links,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"JSON 파일 저장: {json_file}")
        
        # 텍스트 파일로도 저장
        txt_file = output_dir / f"abcmart_links_{keyword}_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"# ABC마트 검색 결과\n")
            f.write(f"# 검색어: {keyword}\n")
            f.write(f"# 수집 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 총 {len(links)}개\n")
            f.write("=" * 50 + "\n\n")
            
            for link in links:
                f.write(f"{link}\n")
                
        logger.info(f"텍스트 파일 저장: {txt_file}")
        
        return json_file, txt_file
        
    def run(self, keyword, max_pages=10):
        """메인 실행 함수"""
        try:
            # 드라이버 설정
            self.setup_driver()
            
            # 검색 실행
            links = self.search_products(keyword, max_pages)
            
            if links:
                # 결과 저장
                json_file, txt_file = self.save_results(links, keyword)
                
                logger.info(f"\n검색 완료!")
                logger.info(f"수집된 링크: {len(links)}개")
                logger.info(f"JSON 파일: {json_file}")
                logger.info(f"텍스트 파일: {txt_file}")
                
                return links
            else:
                logger.warning("검색 결과가 없습니다.")
                return []
                
        except Exception as e:
            logger.error(f"실행 중 오류: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()


def main():
    """메인 함수"""
    import sys
    
    # 명령줄 인자 확인
    if len(sys.argv) > 1:
        keyword = ' '.join(sys.argv[1:])
    else:
        keyword = input("검색어를 입력하세요: ")
        
    if not keyword:
        print("검색어를 입력해야 합니다.")
        return
        
    # 최대 페이지 수
    max_pages = 10
    
    print(f"\nABC마트에서 '{keyword}' 검색을 시작합니다...")
    print(f"최대 {max_pages}페이지까지 검색합니다.\n")
    
    # 스크래퍼 실행
    scraper = ABCMartSearchScraper(headless=False)  # 디버깅을 위해 headless=False
    links = scraper.run(keyword, max_pages)
    
    if links:
        print(f"\n✅ 검색 완료! 총 {len(links)}개의 상품을 찾았습니다.")
        
        # 처음 5개 링크 표시
        print("\n수집된 링크 (처음 5개):")
        for i, link in enumerate(links[:5], 1):
            print(f"{i}. {link}")
        if len(links) > 5:
            print(f"... 외 {len(links) - 5}개")
    else:
        print("\n❌ 검색 결과가 없습니다.")
        
    input("\nEnter를 눌러 종료하세요...")


if __name__ == "__main__":
    main()
