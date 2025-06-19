#!/usr/bin/env python3
"""
K-Fashion 자동 입찰 통합 실행 모듈
기존 프로그램들의 핵심 로직을 import하여 GUI 없이 실행
"""

import os
import sys
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import traceback

# poison_integrated_bidding import 추가
from poison_integrated_bidding import AutoBiddingAdapter

# 로깅 설정
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'unified_bidding_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class UnifiedBidding:
    """통합 입찰 실행 클래스"""
    
    def __init__(self, config_path: str = "config/pricing_strategies.json", debug: bool = False):
        """
        초기화
        
        Args:
            config_path: 가격 전략 설정 파일 경로
            debug: 디버그 모드 활성화 여부
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.db_path = Path("db/bidding.db")
        self.results = {}
        self.debug = debug
        
        # 디버그 모드일 때 로그 레벨 변경
        if self.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("디버그 모드 활성화")
        
        logger.info("UnifiedBidding 초기화 완료")
        
    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {self.config_path}")
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            logger.info(f"설정 파일 로드 완료: {self.config_path}")
            return config
            
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            raise
    
    def run_pipeline(self, site: str = "musinsa", strategy_id: str = "basic", 
                    exec_mode: str = "auto", process_mode: str = "sequential",
                    web_scraping: bool = False, search_keyword: str = None) -> Dict[str, Any]:
        """
        전체 파이프라인 실행
        
        Args:
            site: 대상 사이트 ("musinsa" 또는 "abcmart")
            strategy_id: 사용할 가격 전략 ID
            exec_mode: 실행 모드 ("auto" 또는 "manual")
            process_mode: 처리 방식 ("sequential" 또는 "parallel")
            web_scraping: 웹 스크래핑 사용 여부 (기본값: False)
            search_keyword: 검색 키워드 (web_scraping이 True일 때 사용)
            
        Returns:
            실행 결과 딕셔너리
        """
        start_time = datetime.now()
        logger.info(f"파이프라인 시작: site={site}, strategy={strategy_id}, web_scraping={web_scraping}")
        
        try:
            # 성능 측정을 위한 단계별 시간 기록
            step_times = {}
            
            # 1. 링크 추출
            step_start = datetime.now()
            logger.info("[1/4] 링크 추출 시작...")
            links = self._extract_links(site, web_scraping=web_scraping, search_keyword=search_keyword)
            self.results['links'] = links
            step_times['link_extraction'] = (datetime.now() - step_start).total_seconds()
            logger.info(f"추출된 링크 수: {len(links)} (소요시간: {step_times['link_extraction']:.2f}초)")
            
            # 링크가 없으면 중단
            if not links:
                logger.warning("추출된 링크가 없습니다. 파이프라인을 중단합니다.")
                return {
                    'status': 'error',
                    'error': '추출된 링크가 없습니다',
                    'timestamp': datetime.now().isoformat()
                }
            
            # 2. 상품 정보 스크래핑
            step_start = datetime.now()
            logger.info("[2/4] 스크래핑 시작...")
            items = self._scrape_items(site, links, process_mode)
            self.results['items'] = items
            step_times['scraping'] = (datetime.now() - step_start).total_seconds()
            logger.info(f"스크래핑된 상품 수: {len(items)} (소요시간: {step_times['scraping']:.2f}초)")
            
            # 3. 가격 조정
            step_start = datetime.now()
            logger.info("[3/4] 가격 조정 시작...")
            adjusted_items = self._adjust_prices(items, strategy_id)
            self.results['adjusted_items'] = adjusted_items
            step_times['price_adjustment'] = (datetime.now() - step_start).total_seconds()
            logger.info(f"가격 조정 완료: {len(adjusted_items)}개 (소요시간: {step_times['price_adjustment']:.2f}초)")
            
            # 4. 입찰 실행
            step_start = datetime.now()
            logger.info("[4/4] 입찰 실행 시작...")
            bid_results = self._execute_bidding(site, adjusted_items, exec_mode)
            self.results['bid_results'] = bid_results
            step_times['bidding'] = (datetime.now() - step_start).total_seconds()
            logger.info(f"입찰 실행 완료 (소요시간: {step_times['bidding']:.2f}초)")
            
            # 결과 저장
            step_start = datetime.now()
            self._save_results()
            step_times['saving'] = (datetime.now() - step_start).total_seconds()
            
            # 실행 시간 계산
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 최종 결과
            final_result = {
                'status': 'success',
                'site': site,
                'strategy': strategy_id,
                'total_items': len(items),
                'adjusted_items': len(adjusted_items),
                'successful_bids': sum(1 for r in bid_results if r.get('success', False)),
                'failed_bids': sum(1 for r in bid_results if not r.get('success', False)),
                'execution_time': execution_time,
                'step_times': step_times,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"파이프라인 완료: {execution_time:.2f}초")
            logger.info(f"단계별 소요시간: {json.dumps(step_times, indent=2)}")
            return final_result
            
        except Exception as e:
            logger.error(f"파이프라인 실행 중 오류: {e}")
            logger.error(traceback.format_exc())
            
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _extract_links(self, site: str, web_scraping: bool = False, search_keyword: str = None) -> List[str]:
        """
        링크 추출
        
        Args:
            site: 대상 사이트 ("musinsa" 또는 "abcmart")
            web_scraping: 웹 스크래핑 사용 여부 (기본값: False - 파일 읽기)
            search_keyword: 검색 키워드 (web_scraping이 True일 때 사용)
            
        Returns:
            추출된 링크 리스트
        """
        # 웹 스크래핑 모드
        if web_scraping:
            if site == "abcmart":
                logger.info(f"ABC마트 웹 스크래핑 모드: 검색어='{search_keyword}'")
                
                if not search_keyword:
                    logger.error("웹 스크래핑 모드에서는 search_keyword가 필요합니다.")
                    return []
                
                try:
                    # poison_bidder_wrapper_v2 import
                    from poison_bidder_wrapper_v2 import PoizonBidderWrapperV2
                    
                    # wrapper 인스턴스 생성
                    wrapper = PoizonBidderWrapperV2()
                    
                    # ABC마트 링크 추출 실행
                    start_time = datetime.now()
                    links = wrapper.extract_abcmart_links(
                        search_keyword=search_keyword,
                        max_pages=10  # 최대 10페이지까지 검색
                    )
                    extraction_time = (datetime.now() - start_time).total_seconds()
                    
                    logger.info(f"ABC마트 링크 추출 완료: {len(links)}개 (소요시간: {extraction_time:.2f}초)")
                    
                    # 추출된 링크를 JSON 파일로 저장
                    if links:
                        output_dir = Path("output")
                        output_dir.mkdir(exist_ok=True)
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_file = output_dir / f"abcmart_links_{search_keyword}_{timestamp}.json"
                        
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump({
                                "site": "abcmart",
                                "search_keyword": search_keyword,
                                "extraction_time": extraction_time,
                                "total_count": len(links),
                                "links": links,
                                "timestamp": datetime.now().isoformat()
                            }, f, ensure_ascii=False, indent=2)
                        
                        logger.info(f"링크 저장 완료: {output_file}")
                    
                    return links
                    
                except ImportError as e:
                    logger.error(f"poison_bidder_wrapper_v2 import 실패: {e}")
                    return []
                except Exception as e:
                    logger.error(f"ABC마트 웹 스크래핑 실패: {e}")
                    logger.error(traceback.format_exc())
                    return []
            else:
                logger.warning(f"{site}는 아직 웹 스크래핑을 지원하지 않습니다.")
                return []
        
        # 기존 파일 읽기 방식 (하위 호환성 유지)
        links_file = Path(f"input/{site}_links.txt")
        if not links_file.exists():
            logger.warning(f"링크 파일을 찾을 수 없습니다: {links_file}")
            logger.info("테스트 데이터를 사용합니다.")
            
            # 테스트 데이터
            if site == "musinsa":
                return [
                    "https://www.musinsa.com/products/1234567",
                    "https://www.musinsa.com/products/2345678"
                ]
            else:
                return [
                    "https://abcmart.a-rt.com/product/123456",
                    "https://abcmart.a-rt.com/product/234567"
                ]
        
        # 파일에서 링크 읽기
        with open(links_file, 'r', encoding='utf-8') as f:
            links = [line.strip() for line in f if line.strip()]
            
        return links
    
    def _scrape_items(self, site: str, links: List[str], process_mode: str) -> List[Dict[str, Any]]:
        """상품 정보 스크래핑 - JSON 파일에서 읽기"""
        # 가장 최근의 스크래핑 결과 파일 찾기
        json_pattern = f"{site}_products_*.json"
        json_files = list(Path(".").glob(json_pattern))
        
        if not json_files:
            logger.warning(f"{site} 스크래핑 결과 파일을 찾을 수 없습니다.")
            return []
        
        # 가장 최근 파일 선택
        latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
        logger.info(f"스크래핑 결과 파일 읽기: {latest_file}")
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                scraped_data = json.load(f)
            
            # 데이터 형식 변환 (unified format)
            items = []
            logger.info(f"원본 데이터 수: {len(scraped_data)}개 상품")
            
            for product in scraped_data:
                # 각 사이즈별로 아이템 생성
                for size_info in product.get('sizes_prices', []):
                    if size_info['size'] != '품절':  # 품절 제외
                        items.append({
                            'brand': product['brand'],
                            'code': product['product_code'],
                            'product_code': product['product_code'],  # poison_bidder_wrapper_v2 호환
                            'color': product.get('color', ''),
                            'size': size_info['size'],
                            'price': size_info['price'],
                            'link': product['url'],
                            'stock': True,
                            'scraped_at': product.get('scraped_at', ''),
                            'worker_id': product.get('worker_id', 0)
                        })
            
            logger.info(f"스크래핑 데이터 로드 완료: {len(items)}개 아이템")
            if items:
                logger.debug(f"첫 번째 아이템 예시: {items[0]}")
            return items
            
        except Exception as e:
            logger.error(f"스크래핑 결과 파일 읽기 실패: {e}")
            return []
    
    def _adjust_prices(self, items: List[Dict[str, Any]], strategy_id: str) -> List[Dict[str, Any]]:
        """가격 조정 적용"""
        strategy = self.config['strategies'].get(strategy_id)
        
        if not strategy or not strategy.get('enabled', False):
            logger.warning(f"전략 '{strategy_id}'가 없거나 비활성화되어 있습니다.")
            return items
        
        logger.info(f"가격 전략 '{strategy_id}' 적용 중...")
        adjusted_items = []
        adjustments = strategy.get('adjustments', {})
        
        for item in items:
            adjusted_item = item.copy()
            price = item['price']
            original_price = price
            
            # 각 할인 적용
            for adj_type, adj_config in adjustments.items():
                if adj_config.get('enabled', False):
                    rate = adj_config.get('rate', 0)
                    max_amount = adj_config.get('max_amount', float('inf'))
                    
                    discount = min(price * rate, max_amount)
                    price = price - discount
                    
                    logger.debug(f"{adj_type} 할인 적용: {discount}원")
            
            adjusted_item['adjusted_price'] = int(price)
            adjusted_item['discount_amount'] = original_price - int(price)
            adjusted_item['discount_rate'] = (original_price - int(price)) / original_price
            
            adjusted_items.append(adjusted_item)
            
        return adjusted_items
    
    def _execute_bidding(self, site: str, items: List[Dict[str, Any]], exec_mode: str) -> List[Dict[str, Any]]:
        """포이즌 통합 입찰 실행"""
        logger.info("포이즌 통합 입찰 시스템을 사용한 입찰 실행")
        logger.info(f"입찰 아이템 수: {len(items)}")
        
        # 데이터 검증 및 로깅
        if items:
            sample_item = items[0]
            logger.info(f"샘플 아이템 구조: {list(sample_item.keys())}")
            logger.info(f"샘플 아이템 데이터: {sample_item}")
            
            # 필수 필드 확인
            required_fields = ['code', 'brand', 'size', 'price']
            missing_fields = [field for field in required_fields if field not in sample_item]
            if missing_fields:
                logger.warning(f"누락된 필드: {missing_fields}")
        
        try:
            # items 파라미터 타입 검증
            if not isinstance(items, list):
                error_msg = f"TypeError: items는 list 타입이어야 합니다. 받은 타입: {type(items).__name__}"
                logger.error(error_msg)
                raise TypeError(error_msg)
            
            if not items:
                logger.warning("입찰할 아이템이 없습니다.")
                return []
            
            logger.info(f"run_with_poison 호출 전 최종 확인 - 타입: {type(items)}, 개수: {len(items)}")
            
            # AutoBiddingAdapter를 사용한 입찰 실행
            # Chrome 드라이버 경로 자동 탐색 사용
            adapter = AutoBiddingAdapter(
                driver_path=None,  # 자동 탐색
                min_profit=0,      # 최소 수익 0
                worker_count=5     # 워커 수
            )
            result = adapter.run_with_poison(items)
            
            # 결과 형식 변환
            bid_results = []
            
            # 입찰 결과가 있는 경우
            if result.get('status') == 'success' and 'results' in result:
                for item, res in zip(items, result.get('results', [])):
                    bid_results.append({
                        'item_code': item.get('code'),
                        'success': res.get('success', False),
                        'message': res.get('message', ''),
                        'timestamp': res.get('timestamp', datetime.now().isoformat())
                    })
            else:
                # 에러가 발생한 경우 모든 아이템에 대해 실패 처리
                for item in items:
                    bid_results.append({
                        'item_code': item.get('code'),
                        'success': False,
                        'message': result.get('message', '입찰 실행 실패'),
                        'timestamp': datetime.now().isoformat()
                    })
            
            # 결과 로깅
            successful_count = sum(1 for r in bid_results if r.get('success', False))
            logger.info(f"입찰 완료: 성공 {successful_count}/{len(bid_results)}")
            
            return bid_results
            
        except Exception as e:
            logger.error(f"입찰 실행 중 오류 발생: {e}")
            logger.error(traceback.format_exc())
            
            # 오류 발생 시 모든 아이템에 대해 실패 반환
            return [{
                'item_code': item.get('code'),
                'success': False,
                'message': f'입찰 실행 오류: {str(e)}',
                'timestamp': datetime.now().isoformat()
            } for item in items]
    
    def _save_results(self):
        """결과 저장"""
        try:
            # DB에 이력 저장
            self._save_to_db()
            
            # JSON 파일로도 저장
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"bidding_result_{timestamp}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
                
            logger.info(f"결과 저장 완료: {output_file}")
            
        except Exception as e:
            logger.error(f"결과 저장 실패: {e}")
    
    def _save_to_db(self):
        """DB에 결과 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # bid_history 테이블에 저장
            for item in self.results.get('adjusted_items', []):
                cursor.execute("""
                    INSERT INTO bid_history (
                        site, item_code, brand, color, size,
                        original_price, adjusted_price, strategy_used,
                        bid_status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    'musinsa',  # TODO: 실제 site 값 사용
                    item['code'],
                    item['brand'],
                    item['color'],
                    item['size'],
                    item['price'],
                    item['adjusted_price'],
                    'basic',  # TODO: 실제 strategy 값 사용
                    'success',  # TODO: 실제 상태 사용
                    datetime.now().isoformat()
                ))
            
            conn.commit()
            conn.close()
            
            logger.info("DB 저장 완료")
            
        except Exception as e:
            logger.error(f"DB 저장 실패: {e}")


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='K-Fashion 자동 입찰 통합 실행')
    parser.add_argument('--site', choices=['musinsa', 'abcmart'], default='musinsa',
                        help='대상 사이트')
    parser.add_argument('--strategy', default='basic',
                        help='가격 전략 ID')
    parser.add_argument('--mode', choices=['auto', 'manual'], default='auto',
                        help='실행 모드')
    parser.add_argument('--process', choices=['sequential', 'parallel'], default='sequential',
                        help='처리 방식')
    parser.add_argument('--debug', action='store_true',
                        help='디버그 모드 활성화')
    parser.add_argument('--web-scraping', action='store_true',
                        help='웹 스크래핑 모드 활성화 (ABC마트 지원)')
    parser.add_argument('--search-keyword', type=str,
                        help='검색 키워드 (웹 스크래핑 모드에서 사용)')
    
    args = parser.parse_args()
    
    # 웹 스크래핑 모드 검증
    if args.web_scraping and not args.search_keyword:
        parser.error("웹 스크래핑 모드에서는 --search-keyword가 필요합니다.")
    
    # 실행
    bidder = UnifiedBidding(debug=args.debug)
    result = bidder.run_pipeline(
        site=args.site,
        strategy_id=args.strategy,
        exec_mode=args.mode,
        process_mode=args.process,
        web_scraping=args.web_scraping,
        search_keyword=args.search_keyword
    )
    
    # 결과 출력
    print("\n=== 실행 결과 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 성공/실패 판단
    if result['status'] == 'success':
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
