#!/usr/bin/env python3
"""
K-Fashion 자동 입찰 완전 통합 모듈
링크 추출부터 입찰까지 모든 과정을 자동화
"""

import os
import sys
import json
import logging
import sqlite3
import time
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import traceback
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Selenium for link extraction
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import undetected_chromedriver as uc
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# 로그인 관리자 import
try:
    from login_manager import LoginManager
    LOGIN_MANAGER_AVAILABLE = True
except ImportError:
    LOGIN_MANAGER_AVAILABLE = False
    print("로그인 관리자를 사용할 수 없습니다.")

# 포이즌 통합 입찰 import
try:
    from poison_integrated_bidding import AutoBiddingAdapter
    POISON_LOGIN_AVAILABLE = True
except ImportError:
    POISON_LOGIN_AVAILABLE = False

# ABC마트 멀티프로세스 스크래퍼 import
try:
    from abcmart_scraper_improved_backup import AbcmartMultiprocessScraper, AbcmartWorker
    ABCMART_MULTIPROCESS_AVAILABLE = True
except ImportError:
    ABCMART_MULTIPROCESS_AVAILABLE = False
    print("ABC마트 멀티프로세스 스크래퍼를 사용할 수 없습니다.")

# 로깅 설정
log_dir = Path("C:/poison_final/logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'auto_bidding_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ABC마트 계열 채널 정보
ABC_MART_CHANNELS = {
    'abcmart': {
        'domain': 'abcmart',
        'channel': '10001',
        'name': 'ABC마트'
    },
    'grandstage': {
        'domain': 'grandstage',
        'channel': '10002',
        'name': '그랜드스테이지'
    }
}


class AutoBidding:
    """완전 자동화 입찰 클래스"""
    
    def __init__(self, config_path: str = "config/auto_bidding_config.json"):
        """초기화"""
        self.config = self._load_config(config_path)
        self.driver = None
        self.results = {}
        self.login_manager = None
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """설정 파일 로드"""
        default_config = {
            "search_keywords": {
                "musinsa": ["나이키", "아디다스", "뉴발란스"],
                "abcmart": ["운동화", "스니커즈"]
            },
            "extraction": {
                "max_scrolls": 10,
                "wait_time": 3,
                "max_links": 50,
                "max_pages": 100,
                "page_wait_time": 3,
                "empty_page_threshold": 2
            },
            "pricing": {
                "default_strategy": "basic"
            },
            "scraping": {
                "delay": 2,
                "timeout": 30
            }
        }
        
        config_file = Path(config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                logger.warning(f"설정 파일 로드 실패, 기본값 사용: {e}")
        else:
            # 기본 설정 파일 생성
            config_file.parent.mkdir(exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
                
        return default_config
    
    def _build_page_url(self, base_url: str, page: int) -> str:
        """
        페이지 번호가 포함된 URL 생성
        
        Args:
            base_url: 기본 URL (page 파라미터 있을 수도 없을 수도 있음)
            page: 페이지 번호
            
        Returns:
            page 파라미터가 설정된 새로운 URL
        """
        # URL 파싱
        parsed = urlparse(base_url)
        params = parse_qs(parsed.query)
        
        # page 파라미터 설정 (기존 값 덮어쓰기)
        params['page'] = [str(page)]
        
        # URL 재구성
        new_query = urlencode(params, doseq=True)
        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        
        logger.debug(f"URL 생성: {new_url} (페이지 {page})")
        return new_url
    
    def _build_channel_search_url(self, keyword: str, channel_info: dict, page: int = 1) -> str:
        """
        채널별 검색 URL 생성
        
        Args:
            keyword: 검색 키워드
            channel_info: 채널 정보 딕셔너리 (domain, channel, name 포함)
            page: 페이지 번호 (기본값 1)
            
        Returns:
            채널별 검색 URL
        """
        domain = channel_info['domain']
        channel = channel_info['channel']
        
        # 채널별 URL 생성
        search_url = (
            f"https://{domain}.a-rt.com/display/search-word/result?"
            f"ntab&smartSearchCheck=false&perPage=30&sort=point&"
            f"dfltChnnlMv=&searchPageGubun=product&track=W0010&"
            f"searchWord={keyword}&page={page}&channel={channel}&"
            f"chnnlNo={channel}&tabGubun=total"
        )
        
        logger.debug(f"{channel_info['name']} URL 생성: {search_url[:80]}...")
        return search_url
    
    def _extract_links_from_page(self, site: str, channel_info: Dict[str, str] = None) -> List[str]:
        """
        현재 페이지에서 링크 추출
        
        Args:
            site: 사이트 이름 (abcmart/musinsa)
            channel_info: 채널 정보 (도메인, 채널ID, 이름 포함) - ABC마트 계열에만 사용
            
        Returns:
            추출된 링크 목록
        """
        links = []
        
        try:
            if site == 'abcmart':
                # ABC마트 링크 추출 로직
                # 여러 선택자로 시도
                selectors = [
                    'a[href*="product?prdtNo="]',
                    'a[href*="prdtNo="]',
                    '.item-list a[href]',
                    '.search-list-wrap a[href]',
                    '.item_area a[href]',
                    '.list_item a[href]'
                ]
                
                for selector in selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        href = elem.get_attribute('href')
                        if href and 'prdtNo=' in href:
                            # 상품 번호 추출
                            match = re.search(r'prdtNo=(\d+)', href)
                            if match:
                                product_id = match.group(1)
                                # 표준 형식으로 저장 (채널 정보가 있으면 해당 도메인 사용)
                                if channel_info:
                                    domain = channel_info['domain']
                                    link = f"https://{domain}.a-rt.com/product?prdtNo={product_id}"
                                else:
                                    link = f"https://abcmart.a-rt.com/product?prdtNo={product_id}"
                                if link not in links:
                                    links.append(link)
                
            logger.debug(f"{site}에서 {len(links)}개 링크 추출")
            
        except Exception as e:
            logger.error(f"페이지 링크 추출 오류: {e}")
        
        return links
    
    def run_auto_pipeline(self, site: str = "musinsa", keywords: Optional[List[str]] = None,
                         strategy: str = "basic") -> Dict[str, Any]:
        """
        완전 자동화 파이프라인 실행
        
        Args:
            site: 대상 사이트
            keywords: 검색 키워드 (None이면 설정 파일에서 읽음)
            strategy: 가격 전략
        """
        start_time = datetime.now()
        logger.info(f"자동화 파이프라인 시작: {site}")
        
        try:
            # 1. 링크 자동 추출
            if not keywords:
                keywords = self.config['search_keywords'].get(site, [])
            
            all_links = []
            keyword_stats = {}  # 키워드별 통계
            
            for keyword in keywords:
                logger.info(f"\n키워드 '{keyword}' 검색 중...")
                links = self._extract_links_auto(site, keyword)
                all_links.extend(links)
                keyword_stats[keyword] = len(links)
                logger.info(f"'{keyword}'에서 {len(links)}개 링크 추출")
            
            # 전체 통합 통계
            logger.info(f"\n=== 전체 키워드 통합 결과 ===")
            for keyword, count in keyword_stats.items():
                logger.info(f"- {keyword}: {count}개")
            
            total_before_dedup = len(all_links)
            logger.info(f"\n총 수집 링크: {total_before_dedup}개")
            
            # 중복 제거
            unique_links = list(set(all_links))
            total_duplicates = total_before_dedup - len(unique_links)
            
            if total_duplicates > 0:
                logger.info(f"키워드 간 중복 제거: {total_duplicates}개")
            logger.info(f"최종 고유 링크: {len(unique_links)}개")
            
            # 최대 개수 제한
            max_links = self.config['extraction']['max_links']
            if len(unique_links) > max_links:
                unique_links = unique_links[:max_links]
                logger.info(f"최대 {max_links}개로 제한")
            
            self.results['links'] = unique_links
            
            # 2. 상품 정보 스크래핑
            logger.info("상품 정보 수집 중...")
            items = self._scrape_items_auto(site, unique_links)
            self.results['items'] = items
            logger.info(f"{len(items)}개 상품 정보 수집 완료")
            
            # 3. 가격 조정
            logger.info("가격 조정 중...")
            adjusted_items = self._apply_pricing_strategy(items, strategy)
            self.results['adjusted_items'] = adjusted_items
            
            # 4. 입찰 실행
            logger.info("입찰 실행 중...")
            bid_results = self._execute_auto_bidding(site, adjusted_items)
            self.results['bid_results'] = bid_results
            
            # 결과 저장
            self._save_results()
            
            # 실행 시간
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'status': 'success',
                'site': site,
                'keywords': keywords,
                'total_links': len(unique_links),
                'total_items': len(items),
                'successful_bids': sum(1 for r in bid_results if r.get('success', False)),
                'execution_time': execution_time,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"파이프라인 오류: {e}")
            logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def _extract_links_auto(self, site: str, keyword: str) -> List[str]:
        """자동 링크 추출"""
        if not SELENIUM_AVAILABLE:
            logger.error("Selenium이 설치되지 않았습니다.")
            return []
        
        links = []
        
        try:
            # 로그인 관리자 사용 (ABC마트는 제외)
            if site != 'abcmart' and LOGIN_MANAGER_AVAILABLE and not self.driver:
                logger.info("로그인 확인 중...")
                self.login_manager = LoginManager(site)
                
                # 로그인 상태 확인 및 로그인
                if self.login_manager.ensure_login():
                    self.driver = self.login_manager.driver
                    logger.info("로그인 완료, 검색 시작")
                else:
                    logger.error("로그인 실패")
                    return []
            elif site == 'abcmart' and not self.driver:
                logger.info("ABC마트는 로그인 불필요, 직접 검색 시작")
            
            # 드라이버가 없으면 일반 모드로 초기화
            if not self.driver:
                options = uc.ChromeOptions()
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                
                # Chrome 바이너리 경로 찾기
                chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                    os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                    os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe")
                ]
                
                for chrome_path in chrome_paths:
                    if os.path.exists(chrome_path):
                        options.binary_location = chrome_path
                        break
                
                try:
                    self.driver = uc.Chrome(options=options, version_main=None)
                except Exception as e:
                    logger.error(f"Chrome 드라이버 초기화 실패: {e}")
                    return []
            
            # 검색 URL 구성
            if site == "musinsa":
                search_url = f"https://www.musinsa.com/search/goods?keyword={keyword}"
            else:
                search_url = f"https://abcmart.a-rt.com/display/search-word/result?ntab&smartSearchCheck=false&perPage=30&sort=point&dfltChnnlMv=&searchPageGubun=product&track=W0010&searchWord={keyword}&page=1&channel=10001&chnnlNo=10001&tabGubun=total"
            
            # ABC마트는 페이지네이션, 무신사는 스크롤 방식
            if site == 'abcmart':
                # ABC마트 계열 페이지네이션 방식
                max_pages = self.config['extraction'].get('max_pages', 100)
                page_wait_time = self.config['extraction'].get('page_wait_time', 3)
                empty_threshold = self.config['extraction'].get('empty_page_threshold', 2)
                
                logger.info(f"ABC마트 계열 크롤링 시작 - {len(ABC_MART_CHANNELS)}개 채널")
                
                # 각 채널별 수집 통계
                channel_stats = {}
                
                # 채널별로 순회
                for channel_key, channel_info in ABC_MART_CHANNELS.items():
                    channel_links = []
                    page = 1
                    empty_page_count = 0
                    
                    logger.info(f"\n[{channel_info['name']}] 크롤링 시작 (최대 {max_pages}페이지, 빈 페이지 연속 {empty_threshold}개 시 종료)")
                    logger.info(f"[{channel_info['name']}] 검색어: '{keyword}', 채널 ID: {channel_info['channel']}")
                    
                    while page <= max_pages:
                        # 채널별 URL 생성
                        page_url = self._build_channel_search_url(keyword, channel_info, page)
                        
                        # 페이지 로드
                        self.driver.get(page_url)
                        time.sleep(page_wait_time)
                        
                        # 링크 추출
                        page_links_new = self._extract_links_from_page(site, channel_info)
                        
                        if not page_links_new:
                            empty_page_count += 1
                            logger.info(f"[{channel_info['name']}] 페이지 {page}: 링크 없음 (빈 페이지 {empty_page_count}/{empty_threshold})")
                            
                            # 연속 빈 페이지 임계값 도달 시 종료
                            if empty_page_count >= empty_threshold:
                                logger.info(f"[{channel_info['name']}] 연속 {empty_page_count}개의 빈 페이지, 검색 종료")
                                break
                        else:
                            empty_page_count = 0  # 리셋
                            channel_links.extend(page_links_new)
                            logger.info(f"[{channel_info['name']}] 페이지 {page}: {len(page_links_new)}개 링크 추출 (채널 누적 {len(channel_links)}개)")
                        
                        # 진행 상황 로깅 (10페이지마다)
                        if page % 10 == 0:
                            progress_percent = (page / max_pages) * 100
                            logger.info(f"[{channel_info['name']}] 진행 상황: {page}페이지/{max_pages} ({progress_percent:.1f}%), {len(channel_links)}개 링크 수집")
                        
                        page += 1
                    
                    # 채널별 수집 완료
                    # 채널 내 중복 제거
                    channel_links_unique = list(set(channel_links))
                    duplicates = len(channel_links) - len(channel_links_unique)
                    
                    channel_stats[channel_info['name']] = {
                        'collected': len(channel_links),
                        'unique': len(channel_links_unique),
                        'duplicates': duplicates
                    }
                    logger.info(f"[{channel_info['name']}] 크롤링 완료: 총 {page-1}페이지, {len(channel_links)}개 링크 수집 (중복 제거 후 {len(channel_links_unique)}개, 중복 {duplicates}개)")
                    
                    # 전체 링크 목록에 추가 (중복 제거된 링크)
                    links.extend(channel_links_unique)
                
                # 전체 통계 출력
                logger.info("\n=== ABC마트 계열 크롤링 완료 ===")
                total_collected = sum(stats['collected'] for stats in channel_stats.values())
                total_unique_per_channel = sum(stats['unique'] for stats in channel_stats.values())
                total_duplicates_per_channel = sum(stats['duplicates'] for stats in channel_stats.values())
                
                for channel_name, stats in channel_stats.items():
                    logger.info(f"{channel_name}: 수집 {stats['collected']}개, 고유 {stats['unique']}개, 중복 {stats['duplicates']}개")
                
                logger.info(f"\n채널별 통계 합계:")
                logger.info(f"- 총 수집: {total_collected}개")
                logger.info(f"- 채널 내 중복 제거 후: {total_unique_per_channel}개")
                logger.info(f"- 채널 내 중복: {total_duplicates_per_channel}개")
                logger.info(f"\n전체 통합 결과: {len(links)}개 링크 (채널 간 중복 포함)")
                
                # 채널 간 중복 계산 및 표시
                links_before_dedup = len(links)
                links_unique = list(set(links))
                cross_channel_duplicates = links_before_dedup - len(links_unique)
                
                if cross_channel_duplicates > 0:
                    logger.info(f"\n채널 간 중복 발견: {cross_channel_duplicates}개")
                    logger.info(f"최종 고유 링크 수: {len(links_unique)}개")
                    links = links_unique  # 최종 중복 제거된 링크로 업데이트
                
            else:
                # 무신사 스크롤 방식
                self.driver.get(search_url)
                time.sleep(self.config['extraction']['wait_time'])
                
                # 스크롤하면서 링크 수집
                last_height = self.driver.execute_script("return document.body.scrollHeight")
                
                for i in range(self.config['extraction']['max_scrolls']):
                    # 링크 추출
                    elements = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/products/']")
                    for elem in elements:
                        href = elem.get_attribute('href')
                        if href and '/products/' in href:
                            match = re.search(r'/products/(\d+)', href)
                            if match:
                                product_id = match.group(1)
                                links.append(f"https://www.musinsa.com/products/{product_id}")
                    
                    # 스크롤
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    
                    # 높이 확인
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height
            
        except Exception as e:
            logger.error(f"링크 추출 오류: {e}")
        
        # 최종 중복 제거 및 통계
        final_links_before = len(links)
        final_links = list(set(links))
        final_duplicates = final_links_before - len(final_links)
        
        # 최종 통계 표시
        logger.info(f"\n=== 최종 링크 추출 결과 ({site}) ===")
        logger.info(f"- 총 수집 링크: {final_links_before}개")
        if final_duplicates > 0:
            logger.info(f"- 중복 제거: {final_duplicates}개")
        logger.info(f"- 최종 고유 링크: {len(final_links)}개")
        logger.info(f"- 키워드: '{keyword}'")
        
        return final_links
    
    def _scrape_items_auto(self, site: str, links: List[str]) -> List[Dict[str, Any]]:
        """자동 스크래핑"""
        items = []
        
        # ABC마트의 경우 멀티프로세스 스크래퍼 사용
        if site == "abcmart" and ABCMART_MULTIPROCESS_AVAILABLE:
            logger.info("ABC마트 멀티프로세스 스크래퍼 사용")
            try:
                # 멀티프로세스 스크래퍼 초기화
                scraper = AbcmartMultiprocessScraper(max_workers=5)
                
                # 스크래핑 실행
                products_data = scraper.run_multiprocess(links, output_file=None)
                
                # 데이터 형식 변환
                for product in products_data:
                    if not product or not product.get('sizes_prices'):
                        continue
                    
                    # 각 사이즈별로 아이템 생성
                    for size_info in product['sizes_prices']:
                        item = {
                            'link': product['url'],
                            'brand': product['brand'],
                            'name': product['product_name'],
                            'code': product['product_code'],
                            'color': product.get('color', ''),
                            'size': size_info['size'],
                            'price': size_info['price'],
                            'sizes': [size_info['size']],  # 호환성을 위한 리스트 형태
                            'colors': [product.get('color', '')] if product.get('color') else []
                        }
                        items.append(item)
                
                logger.info(f"ABC마트 멀티프로세스 스크래핑 완료: {len(items)}개 아이템")
                return items
                
            except Exception as e:
                logger.error(f"ABC마트 멀티프로세스 스크래핑 실패: {e}")
                # 실패 시 일반 스크래핑으로 전환
        
        # 일반 스크래핑 (무신사 또는 ABC마트 멀티프로세스 실패 시)
        for i, link in enumerate(links):
            try:
                logger.info(f"스크래핑 {i+1}/{len(links)}: {link}")
                
                if not self.driver:
                    # 드라이버가 없으면 임시 데이터
                    items.append({
                        'link': link,
                        'brand': 'Unknown',
                        'name': f'Product {i+1}',
                        'price': 50000 + (i * 1000),
                        'sizes': ['95', '100', '105'],
                        'colors': ['BLACK', 'WHITE']
                    })
                    continue
                
                # 실제 스크래핑
                self.driver.get(link)
                time.sleep(self.config['scraping']['delay'])
                
                item = {'link': link}
                
                if site == "musinsa":
                    # 무신사 스크래핑
                    try:
                        item['brand'] = self.driver.find_element(By.CSS_SELECTOR, ".product_title em").text
                        item['name'] = self.driver.find_element(By.CSS_SELECTOR, ".product_title strong").text
                        price_text = self.driver.find_element(By.CSS_SELECTOR, ".price").text
                        item['price'] = int(re.sub(r'[^\d]', '', price_text))
                        
                        # 사이즈 옵션
                        size_elements = self.driver.find_elements(By.CSS_SELECTOR, "select[name='size'] option")
                        item['sizes'] = [e.text for e in size_elements if e.text and e.text != '사이즈 선택']
                        
                    except Exception as e:
                        logger.warning(f"상품 정보 추출 실패: {e}")
                        continue
                
                items.append(item)
                
            except Exception as e:
                logger.error(f"스크래핑 오류 {link}: {e}")
                
            # 속도 제한
            if i < len(links) - 1:
                time.sleep(1)
        
        return items
    
    def _apply_pricing_strategy(self, items: List[Dict[str, Any]], strategy: str) -> List[Dict[str, Any]]:
        """가격 전략 적용"""
        # 간단한 가격 조정 로직
        strategies = {
            'basic': 0.95,      # 5% 할인
            'standard': 0.90,   # 10% 할인
            'premium': 0.85     # 15% 할인
        }
        
        discount_rate = strategies.get(strategy, 0.95)
        
        adjusted_items = []
        for item in items:
            adjusted_item = item.copy()
            original_price = item.get('price', 0)
            adjusted_item['adjusted_price'] = int(original_price * discount_rate)
            adjusted_item['discount_amount'] = original_price - adjusted_item['adjusted_price']
            adjusted_items.append(adjusted_item)
        
        return adjusted_items
    
    def _execute_auto_bidding(self, site: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """자동 입찰 실행"""
        results = []
        
        # 포이즌 통합 입찰 사용
        if POISON_LOGIN_AVAILABLE:
            logger.info("포이즌 통합 입찰 시스템 초기화 중...")
            try:
                # AutoBiddingAdapter 사용
                adapter = AutoBiddingAdapter()
                
                # items 파라미터 검증
                if not isinstance(items, list):
                    error_msg = f"TypeError: items는 list 타입이어야 합니다. 받은 타입: {type(items).__name__}"
                    logger.error(error_msg)
                    raise TypeError(error_msg)
                
                if not items:
                    logger.warning("입찰할 아이템이 없습니다.")
                    return []
                
                logger.info(f"run_with_poison 호출 전 items 확인 - 타입: {type(items)}, 개수: {len(items)}")
                logger.debug(f"첫 번째 아이템 샘플: {items[0] if items else 'N/A'}")
                
                # 입찰 목록 준비 (나중에 포이즌 URL로 변환 필요)
                bid_list = []
                for item in items:
                    bid_list.append({
                        'url': item.get('link'),  # TODO: 포이즌 URL로 변환 필요
                        'price': item.get('adjusted_price'),
                        'size': item.get('sizes', ['100'])[0] if item.get('sizes') else '100'
                    })
                
                # 포이즌로 입찰 실행
                bid_result = adapter.run_with_poison(items)
                
                # 결과 변환
                if bid_result['status'] == 'success':
                    results = bid_result.get('results', [])
                    logger.info(f"포이즌 입찰 완료: 성공 {bid_result['successful']}, 실패 {bid_result['failed']}")
                else:
                    logger.error(f"포이즌 입찰 실패: {bid_result.get('message')}")
                    # 실패 시 기본 결과 반환
                    for item in items:
                        results.append({
                            'item': item.get('name', item['link']),
                            'price': item.get('adjusted_price'),
                            'success': False,
                            'message': bid_result.get('message', '포이즌 로그인 실패'),
                            'timestamp': datetime.now().isoformat()
                        })
                
            except Exception as e:
                logger.error(f"포이즌 통합 입찰 오류: {e}")
                # 오류 발생 시 기본 결과 반환
                for item in items:
                    results.append({
                        'item': item.get('name', item['link']),
                        'price': item.get('adjusted_price'),
                        'success': False,
                        'message': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
        else:
            # 포이즌 통합 입찰 없이 시뮬레이션
            logger.warning("포이즌 통합 입찰 모듈이 설치되지 않음. 시뮬레이션 모드로 실행.")
            for item in items:
                result = {
                    'item': item['name'] if 'name' in item else item['link'],
                    'price': item.get('adjusted_price'),
                    'success': True,
                    'message': '입찰 성공 (시뮬레이션)',
                    'timestamp': datetime.now().isoformat()
                }
                results.append(result)
                logger.info(f"입찰: {result['item']} - {result['price']}원")
        
        return results
    
    def _save_results(self):
        """결과 저장"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"auto_bidding_result_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"결과 저장: {output_file}")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='K-Fashion 완전 자동 입찰')
    parser.add_argument('--site', choices=['musinsa', 'abcmart'], default='musinsa',
                        help='대상 사이트')
    parser.add_argument('--keywords', nargs='+', 
                        help='검색 키워드 (예: 나이키 아디다스)')
    parser.add_argument('--strategy', default='basic',
                        help='가격 전략 (basic, standard, premium)')
    
    args = parser.parse_args()
    
    # 실행
    auto_bidder = AutoBidding()
    result = auto_bidder.run_auto_pipeline(
        site=args.site,
        keywords=args.keywords,
        strategy=args.strategy
    )
    
    # 결과 출력
    print("\n=== 자동 입찰 결과 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
