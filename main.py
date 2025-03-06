# 메인 실행 파일 - 프로그램 진입점

import os
import sys
import time
import asyncio
import threading
import importlib
from datetime import datetime, timedelta

# 내부 모듈 임포트
from config import CONFIG, SESSION, STATS, SERVER_STATUS, session_monitor_active
from utils import log, install_playwright_browsers, sync_system_time, update_server_status, wait_until_target_time
from credentials import update_credentials, login_and_get_tokens, check_session, session_monitor_thread, \
    session_refresh_event
from subject import load_subjects, add_subject, SUBJECT_DATA
from notify import send_mobile_alert, send_completion_notification
from request import prepare_request_data, process_requests_with_interval, send_optimized_request
from utils import handle_white_screen


# 초기 설정 확인 및 템플릿 생성
def check_initial_setup():
    """필수 설정 파일 확인 및 생성"""
    # auth_config.py 확인
    if not os.path.exists("auth_config.py"):
        log("⚠️ auth_config.py 파일 없음. 기본 템플릿 생성")
        with open("auth_config.py", "w", encoding="utf-8") as f:
            f.write("""# 인증 정보 설정 파일 - 개인정보 포함 (공유 금지)
# .gitignore에 추가하여 버전 관리 제외 필요

# 수강신청 계정 정보
ID = "학번을_입력하세요"
PW = "비밀번호를_입력하세요"

# 알림 설정
NTFY_TOPIC = "SM-Sugang"  # 알림 토픽 이름
""")
        log("✅ auth_config.py 템플릿 생성 완료. 직접 수정 필요")
        return False

    # 입력된 정보 확인
    try:
        from auth_config import ID, PW
        if ID == "학번을_입력하세요" or PW == "비밀번호를_입력하세요":
            log("⚠️ auth_config.py 파일에 기본값 있음. 실제 정보로 수정 필요")
            return False
    except ImportError:
        log("❌ auth_config.py 파일 손상 또는 필수 변수 없음")
        return False

    # subjects.py 확인
    if not os.path.exists("subjects.py"):
        log("⚠️ subjects.py 파일 없음. 기본 템플릿 생성")
        with open("subjects.py", "w", encoding="utf-8") as f:
            f.write("""# 수강신청 과목 설정 파일
# 학수번호와 분반 관리, .gitignore 추가 권장

# 학수번호:분반 형식으로 작성
subject_data = {
    # 예시: "HALF8002": 1,
    # 여기에 신청할 과목 추가
}

# 우선순위 과목 설정 (빈 리스트는 입력 순서 유지)
priority_subjects = [
    # 예시: "HALF8002",
    # 우선순위 높은 과목 학수번호 추가
]
""")
        log("✅ subjects.py 템플릿 생성 완료. 직접 수정 필요")

    return True


# 10시 정각 접근 최적화
async def prepare_for_peak_time():
    """10시 정각 접근을 위한 최적화된 준비"""
    log("⏱️ 10시 정각 접근 준비 시작...")

    # 시스템 시간 동기화
    sync_system_time()

    # 9:59:45 시점 사전 준비
    now = datetime.now()
    target = now.replace(hour=9, minute=59, second=45, microsecond=0)

    # 대기 처리
    if now < target:
        wait_seconds = (target - now).total_seconds()
        log(f"9:59:45까지 {wait_seconds:.1f}초 대기...")
        await asyncio.sleep(wait_seconds)

    # 로그인 및 세션 준비
    log("🔑 로그인 페이지 사전 준비 시작")
    tokens = await login_and_get_tokens()
    if tokens and tokens["SGJSESSIONID"] and tokens["WMONID"]:
        update_credentials(tokens["SGJSESSIONID"], tokens["WMONID"])
        log("✅ 10시 정각 직전 세션 토큰 획득 완료")
    else:
        log("❌ 세션 토큰 획득 실패, 재시도...")
        tokens = await login_and_get_tokens()
        if tokens and tokens["SGJSESSIONID"] and tokens["WMONID"]:
            update_credentials(tokens["SGJSESSIONID"], tokens["WMONID"])

    # 네트워크 사전 연결
    try:
        import requests
        headers = {
            'Host': 'sugang.smu.ac.kr',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        }

        # 병렬 요청으로 네트워크 준비
        tasks = []
        for _ in range(3):
            task = asyncio.create_task(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: requests.head('https://sugang.smu.ac.kr/index.do',
                                          headers=headers, timeout=1)
                )
            )
            tasks.append(task)

        await asyncio.wait(tasks, timeout=1.5)
        log("✅ 네트워크 준비 완료 (DNS 캐싱, TCP 사전 연결)")
    except Exception as e:
        log(f"⚠️ 네트워크 준비 실패: {e}, 계속 진행")

    # 9:59:55 최종 세션 확인
    now = datetime.now()
    target = now.replace(hour=9, minute=59, second=55, microsecond=0)

    if now < target:
        wait_seconds = (target - now).total_seconds()
        log(f"9:59:55까지 {wait_seconds:.1f}초 대기...")
        await asyncio.sleep(wait_seconds)

    # 세션 확인 및 요청 데이터 준비
    check_session()
    log("📝 요청 데이터 사전 준비 중...")
    prepare_request_data()

    # 10시 정각 카운트다운
    now = datetime.now()
    target = now.replace(hour=10, minute=0, second=0, microsecond=0)

    if now < target:
        wait_seconds = (target - now).total_seconds()
        # 초 단위 카운트다운
        if wait_seconds > 5:
            for i in range(int(wait_seconds), 0, -1):
                log(f"⏱️ 10시 정각까지 {i}초 남음...")
                await asyncio.sleep(1)
        # 정밀 카운트다운
        else:
            log(f"⏱️ 정밀 카운트다운 시작 ({wait_seconds:.3f}초)...")
            while (datetime.now() < target - timedelta(seconds=0.5)):
                remaining = (target - datetime.now()).total_seconds()
                if remaining < 3:
                    log(f"⏱️ 정각까지 {remaining:.3f}초...")
                await asyncio.sleep(0.5)

            # 마지막 0.5초 정밀 대기
            log("🚀 10시 정각 직전...")
            while datetime.now() < target - timedelta(milliseconds=10):
                await asyncio.sleep(0.001)

    log("🔥 10시 정각 도달! 수강신청 시작!")
    return True


# 비동기 수강신청 메인 프로세스
async def async_run_sugang_process():
    """초고속 비동기 수강신청 프로세스 실행"""
    log("🚀 초고속 비동기 수강신청 프로세스 시작...")

    # 통계 및 상태 초기화
    STATS["attempts"] = 0
    STATS["successes"] = 0
    STATS["failures"] = 0
    STATS["session_refreshes"] = 0
    STATS["start_time"] = time.time()
    STATS["request_times"] = []
    STATS["response_times"] = []

    SERVER_STATUS["is_overloaded"] = False
    SERVER_STATUS["consecutive_errors"] = 0
    SERVER_STATUS["backoff_time"] = 0
    SERVER_STATUS["peak_load_detected"] = False
    SERVER_STATUS["white_screen_detected"] = False

    # 세션 모니터링 설정
    global session_refresh_event
    session_refresh_event = threading.Event()
    monitor_thread = threading.Thread(target=session_monitor_thread)
    monitor_thread.daemon = True
    monitor_thread.start()

    # 10시 정각 모드 체크
    is_10am_mode = CONFIG["PEAK_TIME_MODE"]
    now = datetime.now()
    if (now.hour == 9 and now.minute >= 50) or (now.hour == 10 and now.minute < 10):
        is_10am_mode = True

    try:
        # 학수번호 로드 및 확인
        load_subjects()
        if not SUBJECT_DATA:
            log("등록된 학수번호가 없습니다. 학수번호를 추가해주세요.")
            return

        # 10시 정각 모드 처리
        if is_10am_mode:
            log("⏱️ 10시 정각 수강신청 모드 활성화")
            await prepare_for_peak_time()
        else:
            # 일반 모드 준비
            log("초기 세션 토큰 확보 중...")
            if not check_session():
                log("세션 갱신 실패. 재시도...")
                if not check_session():
                    log("세션 갱신 계속 실패. 프로그램 재시작 필요.")
                    return
            prepare_request_data()

        # 수강신청 시작 알림
        subject_list = ", ".join(SUBJECT_DATA.keys())
        send_mobile_alert(f"수강신청 프로세스 시작! 학수번호: {subject_list}")

        # 프로세스 우선순위 상향
        if sys.platform.startswith('win'):
            try:
                import psutil
                p = psutil.Process()
                p.nice(psutil.HIGH_PRIORITY_CLASS)
                log("✅ 프로세스 우선순위 상향 적용")
            except:
                log("⚠️ 프로세스 우선순위 설정 실패")

        # 메인 수강신청 루프
        while SUBJECT_DATA:
            STATS["attempts"] += 1
            cycle_start_time = time.time()
            log(f"🔄 수강신청 시도 #{STATS['attempts']} - 남은 과목: {len(SUBJECT_DATA)}개")

            try:
                # 세션 유효성 확인
                if not SESSION["is_valid"]:
                    log("⚠️ 세션 유효하지 않음. 갱신 중...")
                    session_refresh_event.set()
                    await asyncio.sleep(0.2)

                # 서버 상태 관리
                update_server_status()
                if SERVER_STATUS["white_screen_detected"]:
                    await handle_white_screen()

                # 첫 시도 전략 (0.05초 간격)
                if STATS["attempts"] == 1:
                    log("🚀 첫 시도: 0.05초 간격 전략으로 시도")
                    results = await process_requests_with_interval(SUBJECT_DATA, True)

                    # 성공 확인
                    successful_courses = [c for c, r in results.items()
                                          if "true" in r["response"]]
                    if successful_courses:
                        log(f"🎉 첫 시도 성공! {len(successful_courses)}개 과목 수강신청 완료")
                    else:
                        log("⚠️ 첫 시도 성공한 과목 없음, 재시도 준비 중...")

                    # 세션 상태 확인
                    if not SESSION["is_valid"]:
                        log("⚠️ 세션 유효하지 않음. 갱신 시작...")
                        session_refresh_event.set()
                        await asyncio.sleep(0.3)

                # 후속 시도 (매크로 감지 방지 모드)
                else:
                    # 피크 부하 감지 시 특수 전략
                    if SERVER_STATUS["peak_load_detected"]:
                        log("⚠️ 10시 정각 피크 부하 감지: 신중한 전략으로 전환")
                        log(f"⏱️ 서버 안정화 대기: {2.0:.1f}초")
                        await asyncio.sleep(2.0)

                        # 1개씩 처리
                        for course, div in list(SUBJECT_DATA.items())[:3]:
                            log(f"🔄 피크 부하 모드: 과목 {course} 처리")
                            response = await send_optimized_request(course, div, False)
                            process_response(course, div, response)
                            await asyncio.sleep(1.0)

                        SERVER_STATUS["peak_load_detected"] = False

                    # 일반 과부하 상태
                    elif SERVER_STATUS["is_overloaded"]:
                        log("⚠️ 서버 과부하 감지: 신중한 전략으로 전환")
                        if SERVER_STATUS["backoff_time"] > 0:
                            log(f"⏱️ 서버 과부하 백오프: {SERVER_STATUS['backoff_time']:.1f}초 대기")
                            await asyncio.sleep(SERVER_STATUS["backoff_time"])

                        # 일부 과목만 처리
                        subset_size = min(3, len(SUBJECT_DATA))
                        subset_courses = dict(list(SUBJECT_DATA.items())[:subset_size])
                        log(f"🔄 과부하 모드: {subset_size}개 과목만 처리")
                        results = await process_requests_with_interval(subset_courses, False)

                    # 정상 상태면 전체 과목 처리
                    else:
                        log("🔄 후속 시도: 매크로 감지 방지 모드로 시도")
                        results = await process_requests_with_interval(SUBJECT_DATA, False)

                # 연속 오류 카운터 초기화
                SERVER_STATUS["consecutive_errors"] = 0

                # 다음 사이클 대기
                if SUBJECT_DATA:
                    # 시도 횟수에 따른 가변적 대기 시간
                    if STATS["attempts"] <= 3:
                        wait_time = random.uniform(2, 5)  # 초기: 2-5초
                    elif STATS["attempts"] <= 10:
                        wait_time = random.uniform(5, 15)  # 중기: 5-15초
                    else:
                        wait_time = random.uniform(15, 30)  # 후기: 15-30초

                    # 10시 정각 이후 30초 이내 대기 시간 단축
                    now = datetime.now()
                    if now.hour == 10 and now.minute == 0 and now.second < 30:
                        wait_time = random.uniform(1, 3)  # 10시 직후: 1-3초

                    # 사이클 소요 시간 기록
                    cycle_time = time.time() - cycle_start_time
                    log(f"\n🕒 사이클 #{STATS['attempts']} 완료 (소요: {cycle_time:.2f}초)")
                    log(f"⏱️ 다음 시도까지 {wait_time:.1f}초 대기 (매크로 탐지 방지)\n")
                    await asyncio.sleep(wait_time)

            except asyncio.CancelledError:
                log("⚠️ 비동기 작업이 취소되었습니다.")
                break

            except Exception as e:
                log(f"❌ 사이클 처리 중 오류: {e}")
                STATS["failures"] += 1
                SERVER_STATUS["consecutive_errors"] += 1
                await asyncio.sleep(1)

        # 모든 과목 처리 완료
        elapsed_time = time.time() - STATS["start_time"]
        log(f"✅ 수강신청 프로세스 완료! 소요 시간: {elapsed_time:.1f}초")
        log(f"📊 통계: 시도 {STATS['attempts']}회, 성공 {STATS['successes']}개, 세션 갱신 {STATS['session_refreshes']}회")

        # 성능 분석
        if STATS["request_times"] and STATS["response_times"]:
            avg_response_time = sum(
                [(r - q) * 1000 for q, r in zip(STATS["request_times"], STATS["response_times"])]) / len(
                STATS["request_times"])
            log(f"📊 평균 응답 시간: {avg_response_time:.1f}ms")

        send_completion_notification(STATS["successes"], elapsed_time)

    except KeyboardInterrupt:
        log("⛔ 사용자에 의해 중단됨")
        send_mobile_alert("⛔ 수강신청 프로세스가 중단되었습니다.")

    except Exception as e:
        log(f"❌ 예기치 않은 오류: {e}")
        send_mobile_alert(f"❌ 오류 발생: {str(e)}")

    finally:
        # 정리 작업
        global session_monitor_active
        session_monitor_active = False

        # 프로세스 우선순위 복원
        if sys.platform.startswith('win'):
            try:
                import psutil
                p = psutil.Process()
                p.nice(psutil.NORMAL_PRIORITY_CLASS)
                log("✅ 프로세스 우선순위 복원")
            except:
                pass

        # 최종 결과
        log(f"🏁 수강신청 프로세스 종료. 성공: {CONFIG['success_count']}개")
        if CONFIG['success_count'] > 0:
            send_mobile_alert(f"🎉 수강신청 완료: {CONFIG['success_count']}개 과목 등록 성공")


# 메인 실행 코드
def main():
    """프로그램 진입점"""
    print("=" * 50)
    print("상명대학교 초고속 수강신청 시스템 v3.0 (0.05초 간격 전략)")
    print("=" * 50)

    # 초기 설정 확인
    if not check_initial_setup():
        log("⚠️ 설정 파일 수정 후 재실행 필요")
        input("계속하려면 아무 키나 누르세요...")
        return

    # Playwright 브라우저 설치
    install_playwright_browsers()

    # 타이머 모드 설정
    timer_mode = False
    target_hour = 10
    target_minute = 0

    # 명령행 인자 처리
    if len(sys.argv) > 1:
        if sys.argv[1] == "--timer" or sys.argv[1] == "-t":
            timer_mode = True
            if len(sys.argv) > 2:
                try:
                    time_parts = sys.argv[2].split(":")
                    target_hour = int(time_parts[0])
                    if len(time_parts) > 1:
                        target_minute = int(time_parts[1])
                    log(f"목표 시간이 {target_hour:02d}:{target_minute:02d}:00으로 설정되었습니다.")
                except:
                    log(f"시간 형식 오류. 기본값 10:00 사용")

    # 자격 증명 로드
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("credentials", "credentials.py")
        credentials_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(credentials_module)

        if hasattr(credentials_module, 'SGJSESSIONID') and hasattr(credentials_module, 'WMONID'):
            SESSION["SGJSESSIONID"] = credentials_module.SGJSESSIONID
            SESSION["WMONID"] = credentials_module.WMONID
            log("기존 세션 토큰 로드 완료")
    except (ImportError, AttributeError, FileNotFoundError):
        log("세션 토큰 없음. 로그인 필요")

    # 타이머 모드 대기
    if timer_mode:
        wait_until_target_time(target_hour, target_minute, 0, 0)
        send_mobile_alert(f"{target_hour:02d}:{target_minute:02d}:00 정각에 수강신청을 시작합니다!")

    # 세션 확인 및 갱신
    if not SESSION["SGJSESSIONID"] or not SESSION["WMONID"]:
        log("로그인 시도...")
        loop = asyncio.new_event_loop()
        tokens = loop.run_until_complete(login_and_get_tokens())
        loop.close()

        if tokens and tokens["SGJSESSIONID"] and tokens["WMONID"]:
            update_credentials(tokens["SGJSESSIONID"], tokens["WMONID"])
        else:
            log("로그인 실패. 프로그램 종료")
            exit(1)

    # 테스트 과목 추가
    if not os.path.exists("subjects.py") or len(SUBJECT_DATA) == 0:
        log("테스트용 예시 학수번호 추가")
        add_subject("HALF8002", 1)

    # 시스템 시간 동기화
    sync_system_time()

    # 비동기 수강신청 실행
    asyncio.run(async_run_sugang_process())


if __name__ == "__main__":
    main()