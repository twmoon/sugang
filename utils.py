# 유틸리티 함수 모음

import os
import sys
import time
import threading
import asyncio
from datetime import datetime, timedelta

# Playwright 설치 관련
import playwright._impl._driver
import playwright.sync_api

# 설정 임포트
from config import CONFIG, SESSION, SERVER_STATUS

# 로그 스레드 락
log_lock = threading.Lock()


def log(message, is_debug=False):
    """스레드 안전한 로그 기록"""
    if is_debug and not CONFIG["DEBUG"]:
        return
    with log_lock:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {message}")


def install_playwright_browsers():
    """Playwright 브라우저 자동 설치"""
    log("Playwright 브라우저 설치 확인...")
    try:
        playwright._impl._driver.compute_driver_executable()
        playwright._impl._driver.install_browser("chromium")
        log("Playwright 브라우저 설치 완료!")
        return True
    except Exception as e:
        log(f"Playwright 브라우저 설치 오류: {e}")
        return False


def sync_system_time():
    """NTP 서버로 시스템 시간 동기화"""
    log("🕒 시스템 시간 NTP 동기화 시작...")

    try:
        if sys.platform.startswith('win'):
            # Windows
            os.system('w32tm /resync /force')
            log("✅ Windows 시간 동기화 완료")
        else:
            # Linux/Mac
            try:
                os.system('sudo ntpdate pool.ntp.org')
                log("✅ Linux/Mac 시간 동기화 완료")
            except:
                os.system('ntpdate pool.ntp.org')
                log("✅ 시간 동기화 완료 (sudo 없이)")
        return True
    except Exception as e:
        log(f"⚠️ 시간 동기화 실패: {e}")
        return False


def update_server_status():
    """서버 상태 분석 및 업데이트"""
    # 연속 오류 임계값
    if SERVER_STATUS["consecutive_errors"] >= 3:
        SERVER_STATUS["is_overloaded"] = True
        # 백오프 시간 계산
        SERVER_STATUS["backoff_time"] = min(5, 0.5 * SERVER_STATUS["consecutive_errors"])
        log(f"서버 과부하 상태! 백오프: {SERVER_STATUS['backoff_time']:.1f}초")
    elif SERVER_STATUS["consecutive_errors"] == 0:
        SERVER_STATUS["is_overloaded"] = False
        SERVER_STATUS["backoff_time"] = 0
        log("서버 상태 정상", True)


async def handle_white_screen():
    """흰 화면 발생 시 특수 대응"""
    from credentials import session_refresh_event, check_session

    log("⚠️ 흰 화면 대응 프로토콜 시작...")

    # 세션 갱신
    SESSION["is_valid"] = False
    session_refresh_event.set()
    await asyncio.sleep(0.5)

    # 확인-대기-재시도
    for i in range(3):
        if check_session():
            log("✅ 세션 유효성 확인, 재시도 준비")
            break

        session_refresh_event.set()
        await asyncio.sleep(0.5 * (i + 1))  # 점진적 대기 증가

    SERVER_STATUS["white_screen_detected"] = False
    log("✅ 흰 화면 대응 완료")

    return True


def wait_until_target_time(hour, minute, second=0, microsecond=0):
    """지정 시간까지 정밀 대기"""
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=second, microsecond=microsecond)

    # 이미 지났으면 다음 날로
    if now >= target:
        target = target + timedelta(days=1)

    wait_seconds = (target - now).total_seconds()
    log(f"목표 시간까지 {wait_seconds:.1f}초 (약 {wait_seconds / 60:.1f}분) 대기...")

    # 긴 대기 (1초 간격)
    if wait_seconds > 10:
        while (datetime.now() < target - timedelta(seconds=10)):
            remaining = (target - datetime.now()).total_seconds()
            if int(remaining) % 30 == 0:  # 30초마다 로그
                log(f"남은 시간: {remaining:.1f}초 (약 {remaining / 60:.1f}분)")
            time.sleep(1)

    # 마지막 10초 정밀 대기
    remaining = (target - datetime.now()).total_seconds()
    if remaining > 0:
        log(f"마지막 {remaining:.1f}초 대기...")
        time.sleep(remaining - 0.1)  # 약간 일찍 깨어남

    # 최종 스핀 대기
    while datetime.now() < target:
        pass

    log(f"대기 완료! 정각 {hour:02d}:{minute:02d}:{second:02d}.{microsecond} 도달")
    return True