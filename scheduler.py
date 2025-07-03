#!/usr/bin/env python3
"""
K-Fashion 자동 입찰 스케줄러
APScheduler를 사용한 정기 실행 시스템
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import pytz

# 통합 모듈 import
from unified_bidding import UnifiedBidding

# 로깅 설정
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'scheduler_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class BiddingScheduler:
    """입찰 스케줄러"""
    
    def __init__(self, config_path: str = "config/schedules.json"):
        """초기화"""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.scheduler = BackgroundScheduler(
            timezone=pytz.timezone(self.config['settings']['timezone'])
        )
        self.bidder = UnifiedBidding()
        self.running_jobs = set()
        
        # 이벤트 리스너 등록
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
        
    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 기본 설정
                default_config = {
                    "schedules": [],
                    "settings": {
                        "timezone": "Asia/Seoul",
                        "max_concurrent_jobs": 1,
                        "job_timeout": 3600,
                        "notification": {
                            "on_start": True,
                            "on_complete": True,
                            "on_error": True
                        }
                    }
                }
                self._save_config(default_config)
                return default_config
                
        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            raise
    
    def _save_config(self, config: Optional[Dict] = None):
        """설정 파일 저장"""
        try:
            if config is None:
                config = self.config
                
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                
            logger.info("설정 파일 저장 완료")
            
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
    
    def start(self):
        """스케줄러 시작"""
        logger.info("스케줄러 시작...")
        
        # 저장된 스케줄 로드
        self._load_schedules()
        
        # 스케줄러 시작
        self.scheduler.start()
        logger.info(f"스케줄러 실행 중. 활성 스케줄: {len(self.get_active_schedules())}개")
    
    def stop(self):
        """스케줄러 중지"""
        logger.info("스케줄러 중지...")
        self.scheduler.shutdown(wait=True)
        logger.info("스케줄러 중지 완료")
    
    def _load_schedules(self):
        """저장된 스케줄 로드"""
        for schedule in self.config['schedules']:
            if schedule.get('enabled', False):
                self.add_schedule(schedule, save=False)
    
    def add_schedule(self, schedule_data: Dict[str, Any], save: bool = True) -> bool:
        """스케줄 추가"""
        try:
            schedule_id = schedule_data['id']
            
            # 중복 확인
            if self.scheduler.get_job(schedule_id):
                logger.warning(f"스케줄 {schedule_id}가 이미 존재합니다.")
                return False
            
            # 트리거 생성
            trigger_config = schedule_data['trigger']
            trigger_type = trigger_config['type']
            
            if trigger_type == 'cron':
                trigger = CronTrigger(
                    hour=trigger_config.get('hour'),
                    minute=trigger_config.get('minute'),
                    day_of_week=trigger_config.get('day_of_week'),
                    timezone=self.config['settings']['timezone']
                )
            else:
                logger.error(f"지원하지 않는 트리거 타입: {trigger_type}")
                return False
            
            # Job 추가
            job_config = schedule_data['job']
            self.scheduler.add_job(
                func=self._execute_job,
                trigger=trigger,
                id=schedule_id,
                name=schedule_data['name'],
                kwargs={
                    'schedule_id': schedule_id,
                    'site': job_config['site'],
                    'strategy': job_config['strategy'],
                    'mode': job_config['mode']
                },
                replace_existing=True
            )
            
            logger.info(f"스케줄 추가됨: {schedule_id} - {schedule_data['name']}")
            
            # 설정 파일 업데이트
            if save:
                # 기존 스케줄 찾아서 업데이트 또는 추가
                existing = False
                for i, sch in enumerate(self.config['schedules']):
                    if sch['id'] == schedule_id:
                        self.config['schedules'][i] = schedule_data
                        existing = True
                        break
                
                if not existing:
                    self.config['schedules'].append(schedule_data)
                
                self._save_config()
            
            return True
            
        except Exception as e:
            logger.error(f"스케줄 추가 실패: {e}")
            return False
    
    def remove_schedule(self, schedule_id: str) -> bool:
        """스케줄 제거"""
        try:
            if self.scheduler.get_job(schedule_id):
                self.scheduler.remove_job(schedule_id)
                logger.info(f"스케줄 제거됨: {schedule_id}")
                
                # 설정에서도 제거
                self.config['schedules'] = [
                    sch for sch in self.config['schedules'] 
                    if sch['id'] != schedule_id
                ]
                self._save_config()
                
                return True
            else:
                logger.warning(f"스케줄을 찾을 수 없습니다: {schedule_id}")
                return False
                
        except Exception as e:
            logger.error(f"스케줄 제거 실패: {e}")
            return False
    
    def enable_schedule(self, schedule_id: str) -> bool:
        """스케줄 활성화"""
        for schedule in self.config['schedules']:
            if schedule['id'] == schedule_id:
                schedule['enabled'] = True
                if self.add_schedule(schedule, save=False):
                    self._save_config()
                    return True
        return False
    
    def disable_schedule(self, schedule_id: str) -> bool:
        """스케줄 비활성화"""
        if self.remove_schedule(schedule_id):
            # 설정에서는 유지하되 enabled를 False로
            for schedule in self.config['schedules']:
                if schedule['id'] == schedule_id:
                    schedule['enabled'] = False
            self._save_config()
            return True
        return False
    
    def get_all_schedules(self) -> List[Dict[str, Any]]:
        """모든 스케줄 정보 반환"""
        return self.config['schedules']
    
    def get_active_schedules(self) -> List[Dict[str, Any]]:
        """활성 스케줄 정보 반환"""
        active_jobs = []
        for job in self.scheduler.get_jobs():
            job_info = {
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job.next_run_time else 'N/A',
                'trigger': str(job.trigger)
            }
            active_jobs.append(job_info)
        return active_jobs
    
    def _execute_job(self, schedule_id: str, site: str, strategy: str, mode: str):
        """스케줄된 작업 실행"""
        # 동시 실행 제한
        if len(self.running_jobs) >= self.config['settings']['max_concurrent_jobs']:
            logger.warning(f"최대 동시 실행 수 초과. 작업 건너뜀: {schedule_id}")
            return
        
        self.running_jobs.add(schedule_id)
        start_time = datetime.now()
        
        try:
            logger.info(f"스케줄 작업 시작: {schedule_id}")
            
            # 알림 (시작)
            if self.config['settings']['notification']['on_start']:
                self._send_notification(f"🚀 스케줄 작업 시작: {schedule_id}")
            
            # 입찰 실행
            result = self.bidder.run_pipeline(
                site=site,
                strategy_id=strategy,
                exec_mode=mode
            )
            
            # 결과 로깅
            execution_time = (datetime.now() - start_time).total_seconds()
            
            if result['status'] == 'success':
                logger.info(
                    f"스케줄 작업 완료: {schedule_id} - "
                    f"성공: {result['successful_bids']}, "
                    f"실패: {result['failed_bids']}, "
                    f"시간: {execution_time:.2f}초"
                )
                
                # 알림 (완료)
                if self.config['settings']['notification']['on_complete']:
                    self._send_notification(
                        f"✅ 스케줄 작업 완료: {schedule_id}\n"
                        f"성공: {result['successful_bids']}개"
                    )
            else:
                raise Exception(result.get('error', '알 수 없는 오류'))
                
        except Exception as e:
            logger.error(f"스케줄 작업 실패: {schedule_id} - {e}")
            
            # 알림 (오류)
            if self.config['settings']['notification']['on_error']:
                self._send_notification(f"❌ 스케줄 작업 실패: {schedule_id}\n오류: {e}")
                
        finally:
            self.running_jobs.discard(schedule_id)
    
    def _job_executed(self, event):
        """작업 실행 완료 이벤트"""
        logger.debug(f"작업 실행 완료: {event.job_id}")
    
    def _job_error(self, event):
        """작업 오류 이벤트"""
        logger.error(f"작업 오류 발생: {event.job_id} - {event.exception}")
    
    def _send_notification(self, message: str):
        """알림 전송 (향후 텔레그램 연동)"""
        # TODO: 텔레그램 봇과 연동하여 알림 전송
        logger.info(f"[알림] {message}")
    
    def get_schedule_status(self) -> Dict[str, Any]:
        """스케줄러 상태 정보"""
        return {
            'running': self.scheduler.running,
            'active_schedules': len(self.get_active_schedules()),
            'total_schedules': len(self.config['schedules']),
            'running_jobs': len(self.running_jobs),
            'timezone': str(self.scheduler.timezone)
        }


def main():
    """메인 함수 (테스트용)"""
    import signal
    import time
    
    scheduler = BiddingScheduler()
    
    # 종료 시그널 처리
    def signal_handler(signum, frame):
        logger.info("종료 신호 받음...")
        scheduler.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 스케줄러 시작
    scheduler.start()
    
    # 상태 출력
    print("\n=== K-Fashion 자동 입찰 스케줄러 ===")
    print("Ctrl+C로 종료\n")
    
    status = scheduler.get_schedule_status()
    print(f"타임존: {status['timezone']}")
    print(f"전체 스케줄: {status['total_schedules']}개")
    print(f"활성 스케줄: {status['active_schedules']}개")
    
    print("\n활성 스케줄 목록:")
    for job in scheduler.get_active_schedules():
        print(f"- {job['name']} (ID: {job['id']})")
        print(f"  다음 실행: {job['next_run']}")
    
    # 계속 실행
    try:
        while True:
            time.sleep(60)  # 1분마다 대기
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
