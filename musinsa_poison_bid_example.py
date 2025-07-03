#!/usr/bin/env python3
"""
무신사 상품을 포이즌 입찰 시스템에 적용하는 예제
무신사에서 최대혜택가를 추출하여 포이즌 입찰 데이터로 변환
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append('C:/poison_final')

from poison_bidder_wrapper_v2 import PoizonBidderWrapperV2
from dotenv import load_dotenv

# 로깅 설정
log_dir = Path('C:/poison_final/logs')
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'musinsa_poison_bid_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def create_musinsa_bid_data():
    """무신사 상품 입찰 데이터 생성 예제"""
    
    # 테스트용 무신사 상품 데이터
    # 실제로는 엑셀이나 다른 소스에서 가져올 수 있음
    musinsa_products = [
        {
            "brand": "ADIDAS",
            "code": "IF3904",
            "color": "WHITE",
            "size": "260",
            "url": "https://www.musinsa.com/products/4409450"  # 아디다스 삼바 OG
        },
        {
            "brand": "NIKE",
            "code": "DD1391-100", 
            "color": "WHITE",
            "size": "270",
            "url": "https://www.musinsa.com/products/2545799"  # 나이키 덩크 로우
        },
        {
            "brand": "NEW BALANCE",
            "code": "ML2002RA",
            "color": "GREY",
            "size": "280",
            "url": "https://www.musinsa.com/products/1234567"  # 예시 URL
        }
    ]
    
    logger.info(f"무신사 상품 {len(musinsa_products)}개 처리 시작")
    
    # PoizonBidderWrapperV2 초기화
    wrapper = PoizonBidderWrapperV2(min_profit=3000, worker_count=1)
    
    # 무신사 로그인 확인
    logger.info("무신사 로그인 확인 중...")
    if not wrapper.ensure_musinsa_login():
        logger.error("무신사 로그인 실패")
        return None
    
    logger.info("무신사 로그인 성공")
    
    # 각 상품의 최대혜택가 추출
    bid_data_list = []
    
    for idx, product in enumerate(musinsa_products, 1):
        logger.info(f"\n[{idx}/{len(musinsa_products)}] {product['brand']} {product['code']} 처리 중...")
        
        try:
            # 최대혜택가 추출
            max_benefit_price = wrapper.extract_musinsa_max_benefit_price(product['url'])
            
            if max_benefit_price:
                logger.info(f"최대혜택가: {max_benefit_price:,}원")
                
                # 포이즌 입찰 형식으로 변환
                # (idx, brand, code, color, size, price)
                bid_item = (
                    idx,
                    product['brand'],
                    product['code'],
                    product['color'],
                    product['size'],
                    max_benefit_price
                )
                bid_data_list.append(bid_item)
                
                logger.info(f"입찰 데이터 추가: {bid_item}")
            else:
                logger.warning(f"최대혜택가 추출 실패: {product['url']}")
                
        except Exception as e:
            logger.error(f"상품 처리 중 오류: {e}")
            continue
    
    logger.info(f"\n총 {len(bid_data_list)}개 입찰 데이터 생성 완료")
    
    # 입찰 파일 생성
    if bid_data_list:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"musinsa_bid_{timestamp}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=== 무신사 상품 포이즌 입찰 데이터 ===\n")
            f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("형식: 브랜드,상품코드,색상,사이즈,가격\n")
            f.write("=" * 50 + "\n\n")
            
            for item in bid_data_list:
                # idx 제외하고 브랜드부터 작성
                line = f"{item[1]},{item[2]},{item[3]},{item[4]},{item[5]}\n"
                f.write(line)
        
        logger.info(f"입찰 파일 생성 완료: {output_file}")
        
        return bid_data_list
    else:
        logger.warning("생성된 입찰 데이터가 없습니다")
        return None


def run_poison_bidding_with_musinsa():
    """무신사 데이터로 포이즌 입찰 실행"""
    
    logger.info("=" * 70)
    logger.info("무신사 → 포이즌 자동 입찰 시작")
    logger.info("=" * 70)
    
    # 환경변수 로드
    load_dotenv()
    
    # 1. 무신사 입찰 데이터 생성
    bid_data_list = create_musinsa_bid_data()
    
    if not bid_data_list:
        logger.error("입찰 데이터 생성 실패")
        return
    
    # 2. 포이즌 입찰 실행
    logger.info("\n포이즌 입찰 시작...")
    
    try:
        # PoizonBidderWrapperV2로 입찰 실행
        wrapper = PoizonBidderWrapperV2(min_profit=3000, worker_count=3)
        
        # 입찰 실행
        result = wrapper.run_bidding(bid_data_list=bid_data_list)
        
        # 결과 출력
        if result:
            logger.info("\n입찰 결과:")
            logger.info(f"- 총 처리: {result.get('total_processed', 0)}개")
            logger.info(f"- 성공: {result.get('success_count', 0)}개") 
            logger.info(f"- 실패: {result.get('failed_count', 0)}개")
            logger.info(f"- 소요 시간: {result.get('duration', 'N/A')}")
        
    except Exception as e:
        logger.error(f"포이즌 입찰 중 오류: {e}")
        import traceback
        traceback.print_exc()


def quick_test():
    """빠른 테스트 - 단일 상품"""
    logger.info("=" * 70)
    logger.info("무신사 단일 상품 테스트")
    logger.info("=" * 70)
    
    # 환경변수 로드
    load_dotenv()
    
    # 테스트 상품
    test_product = {
        "brand": "ADIDAS",
        "code": "IF3904",
        "color": "WHITE", 
        "size": "260",
        "url": "https://www.musinsa.com/products/4409450"
    }
    
    # Wrapper 초기화
    wrapper = PoizonBidderWrapperV2(min_profit=3000, worker_count=1)
    
    # 무신사 로그인
    if not wrapper.ensure_musinsa_login():
        logger.error("무신사 로그인 실패")
        return
    
    # 최대혜택가 추출
    logger.info(f"테스트 URL: {test_product['url']}")
    max_benefit_price = wrapper.extract_musinsa_max_benefit_price(test_product['url'])
    
    if max_benefit_price:
        logger.info(f"✅ 최대혜택가: {max_benefit_price:,}원")
        
        # 포이즌 입찰 데이터 생성
        bid_data = [(
            1,
            test_product['brand'],
            test_product['code'],
            test_product['color'],
            test_product['size'],
            max_benefit_price
        )]
        
        logger.info(f"입찰 데이터: {bid_data[0]}")
        
        # 사용자 확인
        user_input = input("\n이 데이터로 포이즌 입찰을 진행하시겠습니까? (y/n): ")
        
        if user_input.lower() == 'y':
            logger.info("\n포이즌 입찰 시작...")
            result = wrapper.run_bidding(bid_data_list=bid_data)
            logger.info("입찰 완료!")
        else:
            logger.info("입찰 취소")
    else:
        logger.error("최대혜택가 추출 실패")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='무신사 상품 포이즌 입찰')
    parser.add_argument('--test', action='store_true', help='단일 상품 테스트')
    parser.add_argument('--full', action='store_true', help='전체 실행')
    
    args = parser.parse_args()
    
    try:
        if args.test:
            quick_test()
        elif args.full:
            run_poison_bidding_with_musinsa()
        else:
            print("\n사용법:")
            print("  python musinsa_poison_bid_example.py --test   # 단일 상품 테스트")
            print("  python musinsa_poison_bid_example.py --full   # 전체 실행")
            print("\n옵션을 선택해주세요.")
            
    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
