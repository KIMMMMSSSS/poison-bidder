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

# 상태 추적을 위한 상수 import
import status_constants

# Selenium for link extraction
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from chrome_driver_manager import initialize_chrome_driver
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

# 무신사 팝업 처리 import
try:
    from musinsa_scraper_improved import enhanced_close_musinsa_popup
    MUSINSA_POPUP_HANDLER_AVAILABLE = True
except ImportError:
    MUSINSA_POPUP_HANDLER_AVAILABLE = False
    print("무신사 팝업 처리기를 사용할 수 없습니다.")

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

# 사이트별 링크 추출 셀렉터
LINK_SELECTORS = {
    'musinsa': [
        'a[href*="/products/"]',
        'a[href*="/app/goods/"]',
        'a[href*="/goods/"]',
        '.list-item__link',
        '.goods-list__link',
        '[class*="product"] a[href*="/products/"]'
    ],
    'abcmart': [
        'a[href*="product?prdtNo="]',
        'a[href*="prdtNo="]',
        '.item-list a[href]',
        '.search-list-wrap a[href]',
        '.item_area a[href]',
        '.list_item a[href]',
        '.product-list a[href*="prdtNo"]',
        '[class*="product"] a[href*="prdtNo"]'
    ]
}

def is_valid_product_link(link: str, site: str) -> bool:
    """
    상품 링크의 유효성 검증
    
    Args:
        link: 검증할 링크
        site: 사이트 이름 (musinsa/abcmart)
        
    Returns:
        bool: 유효한 링크인지 여부
    """
    try:
        if not link or not link.startswith('http'):
            return False
            
        if site == 'musinsa':
            # 무신사 상품 링크 패턴 확인
            if not re.search(r'musinsa\.com/(products|app/goods|goods)/\d+', link):
                return False
            # 제외할 패턴 (리뷰, 이미지 등)
            if any(pattern in link for pattern in ['/review/', '/image/', '/comment/', '#']):
                return False
                
        elif site == 'abcmart':
            # ABC마트 상품 링크 패턴 확인
            if not re.search(r'a-rt\.com/.*prdtNo=\d+', link):
                return False
            # 제외할 패턴
            if any(pattern in link for pattern in ['/review/', '/qna/', '/comment/', '#']):
                return False
                
        return True
        
    except Exception as e:
        logger.debug(f"링크 유효성 검증 오류 ({link}): {e}")
        return False

def normalize_product_link(link: str, site: str, channel_info: Dict[str, str] = None) -> str:
    """
    상품 링크 정규화
    
    Args:
        link: 정규화할 링크
        site: 사이트 이름 (musinsa/abcmart)
        channel_info: 채널 정보 (ABC마트 계열)
        
    Returns:
        str: 정규화된 링크
    """
    try:
        if site == 'musinsa':
            # 무신사 상품 ID 추출
            match = re.search(r'/(?:products|app/goods|goods)/(\d+)', link)
            if match:
                product_id = match.group(1)
                return f"https://www.musinsa.com/products/{product_id}"
                
        elif site == 'abcmart':
            # ABC마트 상품 번호 추출
            match = re.search(r'prdtNo=(\d+)', link)
            if match:
                product_id = match.group(1)
                if channel_info and 'domain' in channel_info:
                    domain = channel_info['domain']
                    return f"https://{domain}.a-rt.com/product?prdtNo={product_id}"
                else:
                    return f"https://abcmart.a-rt.com/product?prdtNo={product_id}"
                    
    except Exception as e:
        logger.debug(f"링크 정규화 오류 ({link}): {e}")
        
    return link


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
                "max_scrolls": 20,
                "scroll_steps": 5,
                "wait_time": 3,
                "max_links": 50,
                "max_pages": 100,
                "page_wait_time": 3,
                "empty_page_threshold": 2,
                "popup_check_interval": 3
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
        extracted_count = 0
        invalid_count = 0
        duplicate_count = 0
        
        try:
            # 사이트별 셀렉터 가져오기
            selectors = LINK_SELECTORS.get(site, [])
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for elem in elements:
                        href = elem.get_attribute('href')
                        if not href:
                            continue
                            
                        extracted_count += 1
                        
                        # 링크 유효성 검증
                        if not is_valid_product_link(href, site):
                            invalid_count += 1
                            continue
                        
                        # 링크 정규화
                        normalized_link = normalize_product_link(href, site, channel_info)
                        
                        # 중복 체크
                        if normalized_link not in links:
                            links.append(normalized_link)
                        else:
                            duplicate_count += 1
                            
                except Exception as e:
                    logger.debug(f"셀렉터 {selector} 처리 중 오류: {e}")
                    continue
            
            # 통계 로깅
            valid_count = len(links)
            logger.info(f"{site} 링크 추출 통계: 총 {extracted_count}개 추출, "
                       f"유효 {valid_count}개, 무효 {invalid_count}개, 중복 {duplicate_count}개")
            
            # 추가 디버그 정보
            if valid_count == 0 and extracted_count > 0:
                logger.warning(f"{site}에서 추출한 링크가 모두 무효합니다. 셀렉터 확인 필요")
            
        except Exception as e:
            logger.error(f"페이지 링크 추출 오류: {e}")
            logger.error(traceback.format_exc())
        
        return links
    
    def run_auto_pipeline(self, site: str = "musinsa", keywords: Optional[List[str]] = None,
                         strategy: str = "basic", status_callback=None,
                         custom_discount_rate: Optional[float] = None,
                         custom_min_profit: Optional[int] = None) -> Dict[str, Any]:
        """
        완전 자동화 파이프라인 실행
        
        Args:
            site: 대상 사이트
            keywords: 검색 키워드 (None이면 설정 파일에서 읽음)
            strategy: 가격 전략
            status_callback: 상태 업데이트 콜백 함수
            custom_discount_rate: 커스텀 할인율 (1-30 범위, None이면 strategy 사용)
            custom_min_profit: 커스텀 최소 수익 (None이면 기본값 사용)
        """
        start_time = datetime.now()
        logger.info(f"자동화 파이프라인 시작: {site}")
        
        # 커스텀 설정 로깅
        if custom_discount_rate is not None:
            logger.info(f"커스텀 할인율: {custom_discount_rate}%")
        if custom_min_profit is not None:
            logger.info(f"커스텀 최소 수익: {custom_min_profit:,}원")
        
        # 초기화 상태 콜백
        if status_callback:
            status_callback(
                status_constants.STAGE_INITIALIZING,
                0,
                f"자동화 파이프라인을 시작합니다. 사이트: {site}"
            )
        
        try:
            # 1. 링크 자동 추출
            if not keywords:
                keywords = self.config['search_keywords'].get(site, [])
            
            all_links = []
            keyword_stats = {}  # 키워드별 통계
            
            # 링크 추출 시작 콜백
            if status_callback:
                status_callback(
                    status_constants.STAGE_LINK_EXTRACTING,
                    10,
                    f"검색 키워드 {len(keywords)}개로 링크 추출을 시작합니다."
                )
            
            for i, keyword in enumerate(keywords):
                logger.info(f"\n키워드 '{keyword}' 검색 중...")
                
                # 각 키워드별 진행률 계산
                keyword_progress = status_constants.calculate_stage_progress(
                    status_constants.STAGE_LINK_EXTRACTING,
                    i + 1,
                    len(keywords)
                )
                
                if status_callback:
                    status_callback(
                        status_constants.STAGE_LINK_EXTRACTING,
                        keyword_progress,
                        f"'{keyword}' 검색 중...",
                        {"current_keyword": keyword, "current_item": i + 1, "total_items": len(keywords)}
                    )
                
                links = self._extract_links_auto(site, keyword, status_callback)
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
            
            # 링크 추출 완료 콜백
            if status_callback:
                status_callback(
                    status_constants.STAGE_LINK_EXTRACTING,
                    30,
                    f"링크 추출 완료: 총 {len(unique_links)}개",
                    {"total_links": len(unique_links)}
                )
            
            # 2. 상품 정보 스크래핑
            logger.info("상품 정보 수집 중...")
            
            # 스크래핑 시작 콜백
            if status_callback:
                status_callback(
                    status_constants.STAGE_SCRAPING,
                    30,
                    f"{len(unique_links)}개 상품의 정보를 수집합니다."
                )
            items = self._scrape_items_auto(site, unique_links, status_callback)
            self.results['items'] = items
            logger.info(f"{len(items)}개 상품 정보 수집 완료")
            
            # 스크래핑 완료 콜백
            if status_callback:
                status_callback(
                    status_constants.STAGE_SCRAPING,
                    70,
                    f"스크래핑 완료: {len(items)}개 상품",
                    {"total_items": len(items)}
                )
            
            # 3. 가격 조정
            logger.info("가격 조정 중...")
            
            # 가격 계산 시작 콜백
            if status_callback:
                status_callback(
                    status_constants.STAGE_PRICE_CALCULATING,
                    70,
                    f"{len(items)}개 상품의 최적 가격을 계산합니다."
                )
            
            adjusted_items = self._apply_pricing_strategy(items, strategy, custom_discount_rate)
            self.results['adjusted_items'] = adjusted_items
            
            # 가격 계산 완료 콜백
            if status_callback:
                status_callback(
                    status_constants.STAGE_PRICE_CALCULATING,
                    80,
                    f"가격 계산 완료: {strategy} 전략 적용"
                )
            
            # 4. 입찰 실행
            logger.info("입찰 실행 중...")
            
            # 입찰 시작 콜백
            if status_callback:
                status_callback(
                    status_constants.STAGE_BIDDING,
                    80,
                    f"{len(adjusted_items)}개 상품 입찰을 시작합니다."
                )
            
            bid_results = self._execute_auto_bidding(site, adjusted_items, status_callback, custom_min_profit, custom_discount_rate)
            self.results['bid_results'] = bid_results
            
            # 입찰 완료 콜백
            successful_bids = sum(1 for r in bid_results if r.get('success', False))
            if status_callback:
                status_callback(
                    status_constants.STAGE_BIDDING,
                    95,
                    f"입찰 완료: {successful_bids}/{len(bid_results)} 성공",
                    {"successful": successful_bids, "total": len(bid_results)}
                )
            
            # 결과 저장
            self._save_results()
            
            # 실행 시간
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 완료 콜백
            if status_callback:
                status_callback(
                    status_constants.STAGE_COMPLETED,
                    100,
                    "모든 작업이 완료되었습니다!",
                    {
                        "total_links": len(unique_links),
                        "total_items": len(items),
                        "successful_bids": successful_bids,
                        "execution_time": execution_time,
                        "custom_discount_rate": custom_discount_rate,
                        "custom_min_profit": custom_min_profit
                    }
                )
            
            return {
                'status': 'success',
                'site': site,
                'keywords': keywords,
                'total_links': len(unique_links),
                'total_items': len(items),
                'successful_bids': successful_bids,
                'execution_time': execution_time,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"파이프라인 오류: {e}")
            logger.error(traceback.format_exc())
            
            # 오류 콜백
            if status_callback:
                status_callback(
                    status_constants.STAGE_ERROR,
                    0,  # 오류 시 진행률은 유지
                    f"오류 발생: {str(e)}",
                    {"error": str(e), "traceback": traceback.format_exc()}
                )
            
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def _extract_links_auto(self, site: str, keyword: str, status_callback=None) -> List[str]:
        """자동 링크 추출"""
        if not SELENIUM_AVAILABLE:
            logger.error("Selenium이 설치되지 않았습니다.")
            return []
        
        links = []
        
        try:
            # 로그인 관리자 사용 (ABC마트는 제외)
            if site != 'abcmart' and LOGIN_MANAGER_AVAILABLE and not self.driver:
                logger.info("로그인 확인 중...")
                
                # 로그인 확인 콜백
                if status_callback:
                    status_callback(
                        status_constants.STAGE_LOGIN_CHECK,
                        5,
                        "로그인 상태를 확인하고 있습니다..."
                    )
                
                self.login_manager = LoginManager(site)
                
                # 로그인 상태 확인 및 로그인
                if self.login_manager.ensure_login():
                    self.driver = self.login_manager.driver
                    logger.info("로그인 완료, 검색 시작")
                    
                    # 로그인 완료 콜백
                    if status_callback:
                        status_callback(
                            status_constants.STAGE_LOGIN_CHECK,
                            10,
                            "로그인 완료"
                        )
                else:
                    logger.error("로그인 실패")
                    return []
            elif site == 'abcmart' and not self.driver:
                logger.info("ABC마트는 로그인 불필요, 직접 검색 시작")
                
                # ABC마트 로그인 불필요 콜백
                if status_callback:
                    status_callback(
                        status_constants.STAGE_LOGIN_CHECK,
                        10,
                        "ABC마트는 로그인이 필요없습니다"
                    )
            
            # 드라이버가 없으면 일반 모드로 초기화
            driver_created_here = False  # 이 메서드에서 드라이버를 생성했는지 추적
            if not self.driver:
                try:
                    # chrome_driver_manager를 사용하여 Chrome 드라이버 초기화
                    self.driver = initialize_chrome_driver(
                        headless=False,  # 일반 모드 (헤드리스 아님)
                        use_undetected=True,  # undetected_chromedriver 사용
                        extra_options=[
                            "--window-size=1920,1080"
                        ]
                    )
                    driver_created_here = True  # 여기서 생성됨을 표시
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
                
                # 무신사 팝업 처리
                if site == "musinsa" and MUSINSA_POPUP_HANDLER_AVAILABLE:
                    try:
                        popup_handled = enhanced_close_musinsa_popup(self.driver, worker_id=None)
                        if popup_handled:
                            logger.info("무신사 팝업 처리 성공")
                        else:
                            logger.debug("무신사 팝업이 없습니다")
                    except Exception as e:
                        logger.warning(f"무신사 팝업 처리 중 예외 (무시하고 계속): {e}")
                
                # 스크롤하면서 링크 수집 - set() 사용으로 자동 중복 제거
                musinsa_links = set()  # set으로 초기화
                last_height = self.driver.execute_script("return document.body.scrollHeight")
                scroll_count = 0
                no_change_count = 0  # 높이 변화 없음 카운트
                
                # 팝업 체크 간격 설정
                popup_check_interval = self.config['extraction'].get('popup_check_interval', 3)
                logger.debug(f"팝업 체크 간격: {popup_check_interval}회마다")
                
                for i in range(self.config['extraction']['max_scrolls']):
                    # Window 상태 체크 (멀티프로세싱 환경에서 window가 닫힐 수 있음)
                    try:
                        current_handles = self.driver.window_handles
                        if not current_handles:
                            logger.warning("브라우저 window가 닫혔습니다. 스크롤 중단")
                            break
                        # 현재 window로 전환 시도
                        self.driver.switch_to.window(current_handles[0])
                    except Exception as e:
                        logger.error(f"Window 상태 체크 실패: {e}")
                        break
                    
                    # 스크롤 전 현재 DOM의 상휸 수 확인
                    products_before_scroll = len(self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/products/']"))
                    logger.debug(f"스크롤 전 DOM 상품 수: {products_before_scroll}개")
                    
                    # 간헐적 팝업 처리 (첫 스크롤 제외)
                    if i > 0 and i % popup_check_interval == 0:
                        if site == "musinsa" and MUSINSA_POPUP_HANDLER_AVAILABLE:
                            try:
                                popup_handled = enhanced_close_musinsa_popup(self.driver, worker_id=None)
                                if popup_handled:
                                    logger.info(f"스크롤 중 팝업 처리 성공 (스크롤 {i+1})")
                                else:
                                    logger.debug(f"스크롤 {i+1}: 팝업 없음")
                            except Exception as e:
                                logger.debug(f"스크롤 중 팝업 처리 예외 (무시): {e}")
                    
                    # 점진적 스크롤 (5단계)
                    scroll_steps = self.config['extraction'].get('scroll_steps', 5)
                    logger.debug(f"점진적 스크롤 시작 ({scroll_steps}단계)")
                    
                    for step in range(scroll_steps):
                        # window.innerHeight의 80%씩 스크롤
                        self.driver.execute_script("window.scrollBy(0, window.innerHeight * 0.8);")
                        time.sleep(0.5)  # 각 단계마다 0.5초 대기
                        
                        # 중간 단계 로깅 (디버그 레벨)
                        if step == scroll_steps - 1:
                            logger.debug(f"  └─ 스크롤 {step + 1}/{scroll_steps} 완료")
                    
                    # 동적 대기: 새 상품이 로드될 때까지 대기 (최대 5초)
                    try:
                        wait = WebDriverWait(self.driver, 5)
                        wait.until(lambda driver: 
                            len(driver.find_elements(By.CSS_SELECTOR, "a[href*='/products/']")) > products_before_scroll
                        )
                        products_after_scroll = len(self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/products/']"))
                        logger.debug(f"새 상품 로드 완료: {products_after_scroll - products_before_scroll}개 추가")
                    except:
                        # 타임아웃 시에도 계속 진행
                        logger.debug("새 상품 로드 대기 타임아웃 (5초)")
                    
                    scroll_count += 1
                    
                    # 로드가 완료된 후 링크 추출
                    page_links = self._extract_links_from_page(site)
                    
                    # 새로운 링크 수 계산 및 추가
                    before_count = len(musinsa_links)
                    musinsa_links.update(page_links)  # set의 update 메서드 사용
                    new_links_count = len(musinsa_links) - before_count
                    
                    # 상세 로깅
                    if new_links_count > 0:
                        logger.info(f"스크롤 {i+1}/{self.config['extraction']['max_scrolls']}: "
                                  f"{new_links_count}개 새 링크 발견 (총 {len(musinsa_links)}개)")
                    else:
                        logger.debug(f"스크롤 {i+1}/{self.config['extraction']['max_scrolls']}: 새 링크 없음")
                    
                    # status_callback 호출 (텔레그램 봇 진행률 업데이트)
                    if status_callback:
                        # 스크롤 진행률 계산 (링크 추출 단계 내에서의 세부 진행률)
                        stage_progress = status_constants.calculate_stage_progress(
                            status_constants.STAGE_LINK_EXTRACTING,
                            i + 1,
                            self.config['extraction']['max_scrolls']
                        )
                        status_callback(
                            status_constants.STAGE_LINK_EXTRACTING,
                            stage_progress,
                            f"스크롤 {i+1}/{self.config['extraction']['max_scrolls']}: "
                            f"{len(musinsa_links)}개 링크 수집 중...",
                            {
                                "current_scroll": i + 1,
                                "total_scrolls": self.config['extraction']['max_scrolls'],
                                "links_found": len(musinsa_links),
                                "new_links": new_links_count
                            }
                        )
                    
                    # 높이 확인 및 무한 스크롤 처리 개선
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    
                    # 높이가 같아도 바로 종료하지 않고 재시도
                    if new_height == last_height:
                        no_change_count += 1
                        logger.debug(f"높이 변화 없음 ({no_change_count}/3)")
                        
                        # 3번 연속으로 높이가 같을 때만 종료
                        if no_change_count >= 3:
                            logger.info(f"페이지 끝 도달 확정 (스크롤 {scroll_count}회, 총 {len(musinsa_links)}개 링크)")
                            break
                        else:
                            # 다시 시도하기 위해 추가 대기
                            logger.info(f"추가 컨텐츠 로드 대기 중... ({no_change_count}/3)")
                            time.sleep(2)  # 추가 대기
                    else:
                        no_change_count = 0  # 높이가 변했으면 카운트 리셋
                        last_height = new_height
                
                # 최종 통계 및 list로 변환하여 병합
                logger.info(f"무신사 링크 추출 완료: 총 {len(musinsa_links)}개 고유 링크 수집")
                links.extend(list(musinsa_links))  # set을 list로 변환하여 추가
            
        except Exception as e:
            logger.error(f"링크 추출 오류: {e}")
            # 오류 발생 시에도 드라이버 종료
            if 'driver_created_here' in locals() and driver_created_here and self.driver:
                try:
                    self.driver.quit()
                    self.driver = None
                except:
                    pass
        
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
        
        # ABC마트의 경우 이 메서드에서 생성한 드라이버는 즉시 종료
        if site == 'abcmart' and driver_created_here and self.driver:
            try:
                logger.info("ABC마트 링크 추출 완료, 드라이버 종료")
                self.driver.quit()
                self.driver = None
            except Exception as e:
                logger.error(f"드라이버 종료 중 오류: {e}")
        
        return final_links
    
    def _scrape_items_auto(self, site: str, links: List[str], status_callback=None) -> List[Dict[str, Any]]:
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
                
                # 스크래핑 진행 상황 콜백
                if status_callback:
                    progress = status_constants.calculate_stage_progress(
                        status_constants.STAGE_SCRAPING,
                        i + 1,
                        len(links)
                    )
                    status_callback(
                        status_constants.STAGE_SCRAPING,
                        progress,
                        f"상품 정보 수집 중... ({i+1}/{len(links)})",
                        {"current_item": i + 1, "total_items": len(links)}
                    )
                
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
                
                # Window 상태 체크 (스크래핑 시작 전)
                try:
                    current_handles = self.driver.window_handles
                    if not current_handles:
                        logger.warning(f"브라우저 window가 닫혔습니다. 스크래핑 중단 ({i+1}/{len(links)})")
                        break
                    # 현재 window로 전환 시도
                    self.driver.switch_to.window(current_handles[0])
                except Exception as e:
                    logger.error(f"Window 상태 체크 실패: {e}")
                    break
                
                # 실제 스크래핑
                self.driver.get(link)
                time.sleep(self.config['scraping']['delay'])
                
                # 무신사 팝업 처리 (각 상품 페이지)
                if site == "musinsa" and MUSINSA_POPUP_HANDLER_AVAILABLE:
                    try:
                        popup_handled = enhanced_close_musinsa_popup(self.driver, worker_id=None)
                        if popup_handled:
                            logger.debug(f"무신사 팝업 처리 성공 (상품 {i+1}/{len(links)})")
                    except Exception as e:
                        logger.debug(f"무신사 팝업 처리 예외 (무시): {e}")
                
                item = {'link': link}
                
                if site == "musinsa":
                    # 무신사 스크래핑 (최신 CSS 셀렉터)
                    try:
                        # 브랜드 추출
                        try:
                            brand_elem = self.driver.find_element(By.CSS_SELECTOR, "a.gtm-click-brand span[data-mds='Typography']")
                            item['brand'] = brand_elem.text.strip()
                            # "브랜드샵 바로가기" 같은 잘못된 텍스트 필터링
                            if "바로가기" in item['brand'] or "브랜드샵" in item['brand']:
                                # href에서 브랜드 추출
                                brand_link = self.driver.find_element(By.CSS_SELECTOR, "a.gtm-click-brand")
                                href = brand_link.get_attribute("href")
                                if "/brand/" in href:
                                    item['brand'] = href.split("/brand/")[-1].upper()
                        except:
                            item['brand'] = "Unknown"
                        
                        # 상품명 추출
                        try:
                            name_elem = self.driver.find_element(By.CSS_SELECTOR, "span[data-mds='Typography'].text-title_18px_med")
                            item['name'] = name_elem.text.strip()
                        except:
                            item['name'] = "Unknown"
                        
                        # 가격 추출 (최대혜택가)
                        try:
                            # JavaScript로 직접 추출
                            price_text = self.driver.execute_script("""
                                const section = document.querySelector('.sc-x9uktx-0.WoXHk');
                                if (section) {
                                    const spans = section.querySelectorAll('span.text-red.text-title_18px_semi');
                                    for (let span of spans) {
                                        if (span.textContent.includes('원') && !span.textContent.includes('%')) {
                                            return span.textContent;
                                        }
                                    }
                                }
                                // 대체 방법: 어떤 가격이든 찾기
                                const priceElem = document.querySelector("span[class*='text-title_18px_semi']:contains('원')");
                                if (priceElem) return priceElem.textContent;
                                
                                // XPath로 시도
                                const xpath = "//span[contains(@class, 'text-red') and contains(text(), '원') and not(contains(text(), '%'))]";
                                const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                                if (result.singleNodeValue) return result.singleNodeValue.textContent;
                                
                                return null;
                            """)
                            
                            if price_text:
                                item['price'] = int(re.sub(r'[^\d]', '', price_text))
                            else:
                                # 대체 방법: 정가 찾기
                                price_elem = self.driver.find_element(By.XPATH, "//span[contains(@class, 'text-title_18px_semi') and contains(text(), '원')]")
                                item['price'] = int(re.sub(r'[^\d]', '', price_elem.text))
                        except Exception as e:
                            logger.debug(f"가격 추출 실패: {e}")
                            item['price'] = 0
                        
                        # 사이즈 추출 (드롭다운 방식)
                        try:
                            sizes = []
                            # 드롭다운 찾기
                            size_dropdown = self.driver.find_element(By.CSS_SELECTOR, "input[data-mds='DropdownTriggerInput'][placeholder='사이즈']")
                            size_dropdown.click()
                            time.sleep(0.5)
                            
                            # 사이즈 옵션 추출
                            size_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-mds='StaticDropdownMenuItem']")
                            for elem in size_elements:
                                text = elem.text.strip()
                                if not text or '(' in text and '품절' in text:
                                    continue
                                # 사이즈 번호만 추출
                                size_match = re.match(r'^(\d+)', text)
                                if size_match:
                                    sizes.append(size_match.group(1))
                            
                            # 드롭다운 닫기
                            self.driver.find_element(By.TAG_NAME, 'body').click()
                            
                            item['sizes'] = sizes if sizes else ['ONE SIZE']
                        except:
                            # 드롭다운이 없으면 원사이즈
                            item['sizes'] = ['ONE SIZE']
                        
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
    
    def _apply_pricing_strategy(self, items: List[Dict[str, Any]], strategy: str,
                               custom_discount_rate: Optional[float] = None) -> List[Dict[str, Any]]:
        """가격 전략 적용"""
        # 간단한 가격 조정 로직
        strategies = {
            'basic': 0.95,      # 5% 할인
            'standard': 0.90,   # 10% 할인
            'premium': 0.85     # 15% 할인
        }
        
        # 커스텀 할인율이 있으면 사용, 없으면 strategy 사용
        if custom_discount_rate is not None:
            discount_rate = 1 - (custom_discount_rate / 100)  # 퍼센트를 비율로 변환
            logger.info(f"커스텀 할인율 적용: {custom_discount_rate}% (비율: {discount_rate})")
        else:
            discount_rate = strategies.get(strategy, 0.95)
        
        adjusted_items = []
        for item in items:
            adjusted_item = item.copy()
            original_price = item.get('price', 0)
            adjusted_item['adjusted_price'] = int(original_price * discount_rate)
            adjusted_item['discount_amount'] = original_price - adjusted_item['adjusted_price']
            adjusted_items.append(adjusted_item)
        
        return adjusted_items
    
    def _execute_auto_bidding(self, site: str, items: List[Dict[str, Any]], status_callback=None,
                             custom_min_profit: Optional[int] = None, custom_discount_rate: Optional[float] = None) -> List[Dict[str, Any]]:
        """자동 입찰 실행"""
        results = []
        
        # 커스텀 최소 수익 로깅
        if custom_min_profit is not None:
            logger.info(f"커스텀 최소 수익 적용: {custom_min_profit:,}원")
        
        # 커스텀 할인율 로깅
        if custom_discount_rate is not None:
            logger.info(f"커스텀 할인율 적용: {custom_discount_rate}%")
        
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
                discount_rate = custom_discount_rate if custom_discount_rate is not None else 0
                bid_result = adapter.run_with_poison(items, status_callback, discount_rate=discount_rate)
                
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
