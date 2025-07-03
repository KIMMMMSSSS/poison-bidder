#!/usr/bin/env python3
"""
_build_page_url 메서드 테스트
"""

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def _build_page_url(base_url: str, page: int) -> str:
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
    
    print(f"URL 생성: {new_url} (페이지 {page})")
    return new_url


# 테스트 케이스들
print("=== _build_page_url 테스트 ===\n")

# 1. page 파라미터가 있는 URL
print("1. page 파라미터가 있는 URL 테스트:")
url1 = "https://abcmart.a-rt.com/display/search-word/result?searchWord=나이키&page=1&perPage=30&sort=point"
result1 = _build_page_url(url1, 5)
print(f"   원본: {url1}")
print(f"   결과: {result1}")
print(f"   → page가 5로 변경되었는지 확인\n")

# 2. page 파라미터가 없는 URL
print("2. page 파라미터가 없는 URL 테스트:")
url2 = "https://abcmart.a-rt.com/display/search-word/result?searchWord=아디다스&perPage=30&sort=point"
result2 = _build_page_url(url2, 3)
print(f"   원본: {url2}")
print(f"   결과: {result2}")
print(f"   → page=3이 추가되었는지 확인\n")

# 3. 복잡한 파라미터를 가진 URL
print("3. 복잡한 파라미터 URL 테스트:")
url3 = "https://abcmart.a-rt.com/display/search-word/result?ntab&smartSearchCheck=false&perPage=30&sort=point&dfltChnnlMv=&searchPageGubun=product&track=W0010&searchWord=운동화&page=2&channel=10001&chnnlNo=10001&tabGubun=total"
result3 = _build_page_url(url3, 10)
print(f"   원본: {url3}")
print(f"   결과: {result3}")
print(f"   → 다른 파라미터들이 보존되고 page만 10으로 변경되었는지 확인\n")

# 4. 파라미터가 전혀 없는 URL
print("4. 파라미터가 없는 URL 테스트:")
url4 = "https://abcmart.a-rt.com/display/search-word/result"
result4 = _build_page_url(url4, 1)
print(f"   원본: {url4}")
print(f"   결과: {result4}")
print(f"   → ?page=1이 추가되었는지 확인\n")

# 5. fragment(#)가 있는 URL
print("5. fragment가 있는 URL 테스트:")
url5 = "https://abcmart.a-rt.com/display/search-word/result?searchWord=뉴발란스&page=3#top"
result5 = _build_page_url(url5, 7)
print(f"   원본: {url5}")
print(f"   결과: {result5}")
print(f"   → fragment(#top)가 보존되고 page가 7로 변경되었는지 확인\n")

print("=== 테스트 완료 ===")
