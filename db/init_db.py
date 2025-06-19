#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite 데이터베이스 초기화 스크립트
K-Fashion 자동 입찰 시스템용 데이터베이스를 생성하고 스키마를 적용합니다.
"""

import sqlite3
import os
import sys
from datetime import datetime
import json

# 데이터베이스 경로 설정
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, 'bidding_history.db')
SCHEMA_PATH = os.path.join(DB_DIR, 'schema.sql')


def init_database():
    """데이터베이스 초기화"""
    print(f"데이터베이스 초기화 시작: {DB_PATH}")
    
    # 데이터베이스 연결 (없으면 자동 생성)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 컬럼명으로 접근 가능하도록 설정
    cursor = conn.cursor()
    
    try:
        # WAL 모드 활성화 (동시 읽기/쓰기 성능 향상)
        cursor.execute("PRAGMA journal_mode=WAL")
        print("[OK] WAL 모드 활성화")
        
        # 외래키 제약 활성화
        cursor.execute("PRAGMA foreign_keys=ON")
        print("[OK] 외래키 제약 활성화")
        
        # 스키마 파일 읽기 및 실행
        if os.path.exists(SCHEMA_PATH):
            with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # SQL 문장들을 개별 실행
            cursor.executescript(schema_sql)
            print("[OK] 스키마 적용 완료")
        else:
            print(f"[WARNING] 스키마 파일을 찾을 수 없습니다: {SCHEMA_PATH}")
            return False
        
        # 기본 가격 전략 추가 (이미 있으면 무시)
        default_strategies = [
            {
                'name': 'basic',
                'config': json.dumps({
                    'coupon': '5%',
                    'points': '1%',
                    'cashback': '2%'
                }, ensure_ascii=False)
            },
            {
                'name': 'standard',
                'config': json.dumps({
                    'coupon': '10%',
                    'points': '2%',
                    'cashback': '3%'
                }, ensure_ascii=False)
            },
            {
                'name': 'premium',
                'config': json.dumps({
                    'coupon': '15%',
                    'points': '3%',
                    'musinsa_card': {'min': 70000, 'discount': 5000},
                    'cashback': '5%'
                }, ensure_ascii=False)
            }
        ]
        
        for strategy in default_strategies:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO pricing_strategies (name, config)
                    VALUES (?, ?)
                """, (strategy['name'], strategy['config']))
            except sqlite3.Error as e:
                print(f"[WARNING] 전략 '{strategy['name']}' 추가 중 오류: {e}")
        
        # 변경사항 저장
        conn.commit()
        print("[OK] 기본 가격 전략 추가 완료")
        
        # 테이블 목록 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("\n생성된 테이블:")
        for table in tables:
            print(f"  - {table['name']}")
            
        # 뷰 목록 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
        views = cursor.fetchall()
        print("\n생성된 뷰:")
        for view in views:
            print(f"  - {view['name']}")
            
        print(f"\n[SUCCESS] 데이터베이스 초기화 완료: {DB_PATH}")
        return True
        
    except sqlite3.Error as e:
        print(f"[ERROR] 데이터베이스 오류: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


def check_database():
    """데이터베이스 상태 확인"""
    if not os.path.exists(DB_PATH):
        print("데이터베이스가 존재하지 않습니다.")
        return False
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # bid_history 테이블 확인
        cursor.execute("SELECT COUNT(*) FROM bid_history")
        count = cursor.fetchone()[0]
        print(f"\nbid_history 테이블: {count}개 레코드")
        
        # pricing_strategies 테이블 확인
        cursor.execute("SELECT name, is_active FROM pricing_strategies")
        strategies = cursor.fetchall()
        print("\n등록된 가격 전략:")
        for name, is_active in strategies:
            status = "활성" if is_active else "비활성"
            print(f"  - {name} ({status})")
            
        return True
        
    except sqlite3.Error as e:
        print(f"데이터베이스 확인 중 오류: {e}")
        return False
        
    finally:
        conn.close()


def reset_database():
    """데이터베이스 초기화 (기존 데이터 삭제)"""
    if os.path.exists(DB_PATH):
        response = input(f"정말로 데이터베이스를 삭제하시겠습니까? [{DB_PATH}] (y/N): ")
        if response.lower() == 'y':
            os.remove(DB_PATH)
            print("기존 데이터베이스가 삭제되었습니다.")
        else:
            print("취소되었습니다.")
            return False
    return True


if __name__ == "__main__":
    # 명령줄 인자 처리
    if len(sys.argv) > 1:
        if sys.argv[1] == "--reset":
            if not reset_database():
                sys.exit(1)
        elif sys.argv[1] == "--check":
            if check_database():
                sys.exit(0)
            else:
                sys.exit(1)
    
    # 데이터베이스 초기화
    if init_database():
        check_database()
    else:
        sys.exit(1)
