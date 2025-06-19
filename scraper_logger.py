"""
간단한 스크래퍼 로거 클래스
abcmart_scraper_improved_backup.py와 musinsa_scraper_improved.py에서 사용
"""

import os
import json
from datetime import datetime
from pathlib import Path


class ScraperLogger:
    """스크래핑 로그 관리 클래스"""
    
    def __init__(self, log_dir="C:/poison_final/logs"):
        """로거 초기화"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 로그 파일 경로
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = self.log_dir / f'scraper_log_{timestamp}.txt'
        self.summary_file = self.log_dir / f'scraper_summary_{timestamp}.json'
        
        # 통계 정보
        self.stats = {
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'total_urls': 0,
            'success': 0,
            'failed': 0,
            'errors': []
        }
    
    def log(self, message):
        """로그 메시지 기록"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        # 콘솔에 출력
        print(message)
        
        # 파일에 기록
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def log_error(self, error_message):
        """에러 로그 기록"""
        self.log(f"ERROR: {error_message}")
        self.stats['errors'].append({
            'timestamp': datetime.now().isoformat(),
            'error': error_message
        })
    
    def log_summary(self, summary):
        """요약 정보 로그"""
        self.stats.update(summary)
        self.save_summary()
    
    def save_summary(self):
        """요약 정보를 JSON 파일로 저장"""
        try:
            with open(self.summary_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"요약 저장 실패: {e}")
    
    def get_stats(self):
        """통계 정보 반환"""
        return self.stats
