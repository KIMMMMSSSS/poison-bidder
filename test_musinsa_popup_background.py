#!/usr/bin/env python3
"""
무신사 팝업 처리 개선 - 배경 하얗게 되는 문제 해결
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
import os

def test_popup_background_issue():
    """무신사 팝업 제거 후 배경 문제 테스트"""
    
    # 드라이버 초기화
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Chrome 경로 설정
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    
    for chrome_path in chrome_paths:
        if os.path.exists(chrome_path):
            options.binary_location = chrome_path
            break
    
    driver = uc.Chrome(options=options, version_main=None)
    
    try:
        print("무신사 페이지 접속...")
        driver.get("https://www.musinsa.com/search/goods?keyword=나이키")
        time.sleep(3)
        
        # 현재 페이지 상태 캡처
        print("\n=== 팝업 제거 전 페이지 상태 ===")
        page_state_before = driver.execute_script("""
            const state = {
                bodyOverflow: window.getComputedStyle(document.body).overflow,
                bodyPosition: window.getComputedStyle(document.body).position,
                bodyBackground: window.getComputedStyle(document.body).backgroundColor,
                bodyFilter: window.getComputedStyle(document.body).filter,
                bodyClasses: Array.from(document.body.classList),
                htmlOverflow: window.getComputedStyle(document.documentElement).overflow,
                dimmedLayers: [],
                overlays: []
            };
            
            // dimmed layer 찾기
            const allElements = document.querySelectorAll('*');
            allElements.forEach(elem => {
                const style = window.getComputedStyle(elem);
                const bg = style.backgroundColor;
                const position = style.position;
                const zIndex = parseInt(style.zIndex) || 0;
                
                // 반투명 백그라운드 찾기
                if (bg.includes('rgba') && position === 'fixed' && zIndex > 1000) {
                    state.dimmedLayers.push({
                        tag: elem.tagName,
                        class: elem.className,
                        bg: bg,
                        zIndex: zIndex
                    });
                }
                
                // overlay 클래스 찾기
                if (elem.className && elem.className.toString().toLowerCase().includes('overlay')) {
                    state.overlays.push({
                        tag: elem.tagName,
                        class: elem.className,
                        display: style.display
                    });
                }
            });
            
            return state;
        """)
        
        print(f"Body overflow: {page_state_before['bodyOverflow']}")
        print(f"Body position: {page_state_before['bodyPosition']}")
        print(f"Body background: {page_state_before['bodyBackground']}")
        print(f"Body filter: {page_state_before['bodyFilter']}")
        print(f"Body classes: {page_state_before['bodyClasses']}")
        print(f"Dimmed layers: {len(page_state_before['dimmedLayers'])}")
        print(f"Overlays: {len(page_state_before['overlays'])}")
        
        # 개선된 팝업 제거 로직
        print("\n=== 개선된 팝업 제거 실행 ===")
        removal_result = driver.execute_script("""
            const results = {
                removedPopups: 0,
                removedBackdrops: 0,
                removedDimmed: 0,
                restoredStyles: []
            };
            
            // 1. 모든 팝업 관련 요소 제거
            const popupSelectors = [
                '.modal', '.popup', '.layer-popup', 
                '.modal-backdrop', '.overlay',
                '[role="dialog"]', '[aria-modal="true"]',
                '.dimmed', '.dim-layer', '.popup-dim'
            ];
            
            popupSelectors.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(elem => {
                    elem.style.display = 'none';
                    elem.remove();
                    results.removedPopups++;
                });
            });
            
            // 2. position:fixed + 반투명 배경 요소 제거
            const allElements = document.querySelectorAll('*');
            allElements.forEach(elem => {
                const style = window.getComputedStyle(elem);
                const bg = style.backgroundColor;
                const position = style.position;
                const zIndex = parseInt(style.zIndex) || 0;
                
                // 반투명 백드롭 제거
                if (position === 'fixed' && zIndex > 999) {
                    if (bg.includes('rgba') || bg.includes('rgb')) {
                        // header나 navigation이 아닌 경우만
                        const tagName = elem.tagName.toLowerCase();
                        const className = elem.className.toString().toLowerCase();
                        if (!tagName.includes('header') && !tagName.includes('nav') &&
                            !className.includes('header') && !className.includes('nav')) {
                            elem.style.display = 'none';
                            elem.remove();
                            results.removedBackdrops++;
                        }
                    }
                }
                
                // dimmed 효과 제거
                if (style.opacity !== '1' && position === 'fixed' && zIndex > 999) {
                    elem.style.display = 'none';
                    elem.remove();
                    results.removedDimmed++;
                }
            });
            
            // 3. body/html 스타일 완전 복원
            // body 스타일 초기화
            document.body.style.cssText = '';
            document.body.style.overflow = 'visible';
            document.body.style.position = 'static';
            document.body.style.filter = 'none';
            document.body.style.backgroundColor = 'transparent';
            
            // html 스타일 초기화
            document.documentElement.style.overflow = 'visible';
            document.documentElement.style.filter = 'none';
            
            // 모든 클래스 제거 후 필요한 것만 복원
            const bodyClasses = Array.from(document.body.classList);
            bodyClasses.forEach(cls => {
                if (cls.includes('modal') || cls.includes('popup') || 
                    cls.includes('open') || cls.includes('fixed') ||
                    cls.includes('scroll') || cls.includes('dim')) {
                    document.body.classList.remove(cls);
                    results.restoredStyles.push(`Removed class: ${cls}`);
                }
            });
            
            // 4. 가상 요소 제거 (::before, ::after)
            const style = document.createElement('style');
            style.textContent = `
                body::before, body::after,
                html::before, html::after {
                    display: none !important;
                    content: none !important;
                }
            `;
            document.head.appendChild(style);
            
            // 5. 강제 리플로우
            document.body.offsetHeight;
            
            // 6. 스크롤 복원
            window.scrollTo(0, 100);
            window.scrollTo(0, 0);
            
            return results;
        """)
        
        print(f"제거된 팝업: {removal_result['removedPopups']}")
        print(f"제거된 백드롭: {removal_result['removedBackdrops']}")
        print(f"제거된 dimmed: {removal_result['removedDimmed']}")
        print(f"복원된 스타일: {len(removal_result['restoredStyles'])}")
        
        # 제거 후 상태 확인
        print("\n=== 팝업 제거 후 페이지 상태 ===")
        page_state_after = driver.execute_script("""
            return {
                bodyOverflow: window.getComputedStyle(document.body).overflow,
                bodyPosition: window.getComputedStyle(document.body).position,
                bodyBackground: window.getComputedStyle(document.body).backgroundColor,
                bodyFilter: window.getComputedStyle(document.body).filter,
                bodyClasses: Array.from(document.body.classList),
                canScroll: document.body.scrollHeight > window.innerHeight
            };
        """)
        
        print(f"Body overflow: {page_state_after['bodyOverflow']}")
        print(f"Body position: {page_state_after['bodyPosition']}")
        print(f"Body background: {page_state_after['bodyBackground']}")
        print(f"Body filter: {page_state_after['bodyFilter']}")
        print(f"Body classes: {page_state_after['bodyClasses']}")
        print(f"스크롤 가능: {page_state_after['canScroll']}")
        
        # 스크롤 테스트
        print("\n스크롤 테스트 중...")
        for i in range(3):
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(0.5)
        
        print("테스트 완료!")
        input("Enter를 눌러 종료...")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        driver.quit()

if __name__ == "__main__":
    test_popup_background_issue()
