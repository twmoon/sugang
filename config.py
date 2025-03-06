# 시스템 설정 및 전역 변수 관리 파일

import time
from datetime import datetime

# 시스템 전역 설정
CONFIG = {
    "MAX_RETRIES": 5,  # 재시도 횟수
    "REQUEST_TIMEOUT": 2,  # 타임아웃 (초)
    "RETRY_INTERVAL": 0.05,  # 재시도 간격
    "SUBJECT_INTERVAL": 0.05,  # 과목 간 간격 (첫 시도)
    "SUBJECT_INTERVAL_JITTER": 0.01,  # 간격 변동 (매크로 탐지 회피)
    "DEBUG": True,  # 디버그 모드
    "success_count": 0,  # 성공 카운트
    "MAX_THREADS": 10,  # 최대 동시 요청 수
    "PEAK_TIME_MODE": True,  # 10시 정각 모드 활성화
    "PRIORITY_SUBJECTS": []  # 우선순위 과목
}

# 세션 상태 관리
SESSION = {
    "SGJSESSIONID": "",  # 세션 ID
    "WMONID": "",  # 모니터링 ID
    "is_valid": False,  # 세션 유효성
    "last_check": 0,  # 마지막 세션 체크 시간
    "check_interval": 1,  # 세션 체크 간격 (초)
    "login_in_progress": False,  # 로그인 진행 중 플래그
    "token_check_count": 0,  # 세션 토큰 확인 횟수
    "last_token_refresh": 0,  # 마지막 토큰 갱신 시간
    "token_validity": 0  # 토큰 유효성 (0: 미확인, 1: 유효, -1: 무효)
}

# 요청 통계
STATS = {
    "attempts": 0,  # 시도 횟수
    "successes": 0,  # 성공 횟수
    "failures": 0,  # 실패 횟수
    "session_refreshes": 0,  # 세션 갱신 횟수
    "start_time": None,  # 시작 시간
    "request_times": [],  # 요청 시간 기록
    "response_times": []  # 응답 시간 기록
}

# 서버 상태 모니터링
SERVER_STATUS = {
    "is_overloaded": False,  # 서버 과부하 상태
    "last_response_time": 0,  # 마지막 응답 시간
    "consecutive_errors": 0,  # 연속 오류 수
    "backoff_time": 0,  # 백오프 타임
    "peak_load_detected": False,  # 10시 정각 피크 부하 감지
    "white_screen_detected": False  # 흰 화면 감지
}

# 전역 변수
session_monitor_active = False  # 세션 모니터링 상태
optimized_headers = {}  # 최적화된 헤더
encoded_request_data = {}  # 인코딩된 요청 데이터