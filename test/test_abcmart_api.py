#!/usr/bin/env python3
"""ABC마트 링크 추출 간단 테스트"""

import requests
from bs4 import BeautifulSoup

def test_abcmart_api():
    """ABC마트 API 테스트"""
    print("ABC마트 검색 API 테스트...")
    
    keyword = "뉴발란스"
    
    # ABC마트 검색 URL
    url = f"https://abcmart.a-rt.com/display/search-word/result?ntab&smartSearchCheck=false&perPage=30&sort=point&dfltChnnlMv=&searchPageGubun=product&track=W0010&searchWord={keyword}&page=1&channel=10001&chnnlNo=10001&tabGubun=total"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            # HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 상품 링크 찾기
            product_links = []
            
            # 다양한 패턴으로 링크 찾기
            patterns = [
                {'name': 'a', 'href': True},  # 모든 a 태그
            ]
            
            for pattern in patterns:
                links = soup.find_all(**pattern)
                for link in links:
                    href = link.get('href', '')
                    if '/product/detail/' in href or 'prdtCode=' in href:
                        full_url = href if href.startswith('http') else f"https://abcmart.a-rt.com{href}"
                        product_links.append(full_url)
                        if len(product_links) <= 5:
                            print(f"찾은 링크: {full_url}")
            
            print(f"\n총 {len(product_links)}개의 상품 링크를 찾았습니다.")
            
            if not product_links:
                print("\n페이지 HTML 샘플:")
                print(response.text[:1000])
        else:
            print(f"요청 실패: {response.status_code}")
            
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    test_abcmart_api()
