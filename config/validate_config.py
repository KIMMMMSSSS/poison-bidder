#!/usr/bin/env python3
"""
가격 전략 설정 파일 검증 스크립트
JSON 구조와 필수 필드를 검증합니다.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List


class ConfigValidator:
    """설정 파일 검증 클래스"""
    
    def __init__(self, config_path: str = "pricing_strategies.json"):
        self.config_path = Path(config_path)
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self) -> bool:
        """설정 파일 검증 메인 함수"""
        # 파일 존재 여부 확인
        if not self.config_path.exists():
            self.errors.append(f"설정 파일이 존재하지 않습니다: {self.config_path}")
            return False
        
        # JSON 파싱
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"JSON 파싱 오류: {e}")
            return False
        except Exception as e:
            self.errors.append(f"파일 읽기 오류: {e}")
            return False
        
        # 구조 검증
        if not self._validate_structure(config):
            return False
        
        # 전략 검증
        strategies = config.get('strategies', {})
        if not strategies:
            self.errors.append("전략이 정의되지 않았습니다")
            return False
        
        for strategy_id, strategy in strategies.items():
            self._validate_strategy(strategy_id, strategy)
        
        return len(self.errors) == 0
    
    def _validate_structure(self, config: Dict[str, Any]) -> bool:
        """기본 구조 검증"""
        if not isinstance(config, dict):
            self.errors.append("최상위 구조는 딕셔너리여야 합니다")
            return False
        
        if 'strategies' not in config:
            self.errors.append("'strategies' 키가 필요합니다")
            return False
        
        if not isinstance(config['strategies'], dict):
            self.errors.append("'strategies'는 딕셔너리여야 합니다")
            return False
        
        return True
    
    def _validate_strategy(self, strategy_id: str, strategy: Dict[str, Any]):
        """개별 전략 검증"""
        required_fields = ['name', 'description', 'enabled', 'adjustments']
        
        # 필수 필드 확인
        for field in required_fields:
            if field not in strategy:
                self.errors.append(f"전략 '{strategy_id}'에 필수 필드 '{field}'가 없습니다")
        
        # adjustments 검증
        if 'adjustments' in strategy:
            adjustments = strategy['adjustments']
            if not isinstance(adjustments, dict):
                self.errors.append(f"전략 '{strategy_id}'의 adjustments는 딕셔너리여야 합니다")
            else:
                self._validate_adjustments(strategy_id, adjustments)
        
        # 숫자 필드 검증
        if 'total_max_discount_rate' in strategy:
            rate = strategy['total_max_discount_rate']
            if not isinstance(rate, (int, float)) or rate < 0 or rate > 1:
                self.warnings.append(f"전략 '{strategy_id}'의 total_max_discount_rate는 0-1 사이여야 합니다")
    
    def _validate_adjustments(self, strategy_id: str, adjustments: Dict[str, Any]):
        """할인 옵션 검증"""
        valid_adjustment_types = ['coupon', 'point', 'musinsa_card', 'cashback']
        
        for adj_type, adj_data in adjustments.items():
            if adj_type not in valid_adjustment_types:
                self.warnings.append(f"전략 '{strategy_id}'에 알 수 없는 할인 타입: {adj_type}")
            
            if isinstance(adj_data, dict):
                # 할인 옵션 필수 필드
                required_adj_fields = ['enabled', 'rate', 'max_amount']
                for field in required_adj_fields:
                    if field not in adj_data:
                        self.errors.append(f"전략 '{strategy_id}'의 '{adj_type}'에 필수 필드 '{field}'가 없습니다")
                
                # rate 검증
                if 'rate' in adj_data:
                    rate = adj_data['rate']
                    if not isinstance(rate, (int, float)) or rate < 0 or rate > 1:
                        self.warnings.append(f"전략 '{strategy_id}'의 '{adj_type}' rate는 0-1 사이여야 합니다")
    
    def print_report(self):
        """검증 결과 출력"""
        print("=== 가격 전략 설정 검증 결과 ===\n")
        
        if self.errors:
            print("[오류]")
            for error in self.errors:
                print(f"  - {error}")
            print()
        
        if self.warnings:
            print("[경고]")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()
        
        if not self.errors and not self.warnings:
            print("[성공] 설정 파일이 유효합니다!")
        
        print(f"\n검증 파일: {self.config_path.absolute()}")


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='가격 전략 설정 파일 검증')
    parser.add_argument('--config', '-c', default='pricing_strategies.json',
                        help='검증할 설정 파일 경로')
    
    args = parser.parse_args()
    
    validator = ConfigValidator(args.config)
    is_valid = validator.validate()
    validator.print_report()
    
    # 오류가 있으면 비정상 종료
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
