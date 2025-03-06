# 요청 관련 기능 모듈

import json
import random
import asyncio
import urllib.request
import urllib.parse
import concurrent.futures
from datetime import datetime

from config import CONFIG, SESSION, STATS, SERVER_STATUS, optimized_headers, encoded_request_data
from utils import log
from notify import send_mobile_alert, send_success_notification, send_session_expired_notification
from credentials import session_refresh_event
from subject import remove_subject, SUBJECT_DATA


def prepare_request_data():
    """과목별 요청 데이터 사전 준비"""
    log("📝 요청 데이터 사전 생성 시작...")

    # 공통 헤더 준비
    global optimized_headers
    optimized_headers = {
        'Host': 'sugang.smu.ac.kr',
        'Cookie': f'WMONID={SESSION["WMONID"]}; SGJSESSIONID={SESSION["SGJSESSIONID"]}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
        'Origin': 'https://sugang.smu.ac.kr',
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive'
    }

    # 과목별 요청 데이터 인코딩
    global encoded_request_data
    encoded_request_data = {}

    for course, div in SUBJECT_DATA.items():
        # 요청 데이터 준비
        data = {
            '_AUTH_MENU_KEY': '',
            '@d1#strCampusRcd': 'CMN001.0001',
            '@d1#strSbjNo': course,
            '@d1#strDivcls': str(div),
            '@d#': '@d1#',
            '@d1#': 'dmParamTlsnAplyDirect',
            '@d1#tp': 'dm'
        }

        # 데이터 미리 인코딩
        encoded_request_data[course] = urllib.parse.urlencode(data).encode('utf-8')

    log(f"✅ {len(encoded_request_data)}개 과목의 요청 데이터 준비 완료")
    return encoded_request_data


async def send_optimized_request(course, div, is_first_attempt=False):
    """0.05초 간격 전략 최적화 요청 함수"""
    # 인코딩된 요청 데이터 사용
    data_encoded = encoded_request_data.get(course)
    if not data_encoded:
        # 없으면 즉시 생성
        data = {
            '_AUTH_MENU_KEY': '',
            '@d1#strCampusRcd': 'CMN001.0001',
            '@d1#strSbjNo': course,
            '@d1#strDivcls': str(div),
            '@d#': '@d1#',
            '@d1#': 'dmParamTlsnAplyDirect',
            '@d1#tp': 'dm'
        }
        data_encoded = urllib.parse.urlencode(data).encode('utf-8')

    # 타임아웃 설정
    request_timeout = 1.0 if is_first_attempt else CONFIG["REQUEST_TIMEOUT"]

    try:
        # 요청 시간 기록
        start_time = datetime.now().timestamp()
        STATS["request_times"].append(start_time)

        # 동기 코드를 비동기에서 실행하기 위한 래퍼
        def send_request():
            try:
                # 요청 객체 생성
                req = urllib.request.Request(
                    url='https://sugang.smu.ac.kr/UcrTlsn/tlsnAplyDirect.do',
                    data=data_encoded,
                    headers=optimized_headers,
                    method='POST'
                )

                # 연결 최적화
                opener = urllib.request.build_opener()
                opener.addheaders = [('Connection', 'keep-alive')]

                # 요청 전송
                with opener.open(req, timeout=request_timeout) as response:
                    response_data = response.read().decode('utf-8')
                    # 응답 시간 기록
                    end_time = datetime.now().timestamp()
                    STATS["response_times"].append(end_time)
                    return response_data

            except urllib.error.HTTPError as e:
                # HTTP 오류 처리
                if hasattr(e, 'read'):
                    error_content = e.read().decode('utf-8', errors='ignore')
                    if error_content:
                        return f"HTTP Error {e.code}: {error_content}"
                raise e
            except Exception as e:
                raise e

        # 첫 시도는 더 높은 우선순위로 처리
        if is_first_attempt:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                response_text = await asyncio.get_event_loop().run_in_executor(executor, send_request)
        else:
            # 일반 실행
            response_text = await asyncio.get_event_loop().run_in_executor(None, send_request)

        return response_text

    except Exception as e:
        error_msg = str(e)
        if is_first_attempt:
            log(f"⚠️ 네트워크 오류 (과목 {course}): {error_msg[:100]}...", True)
        else:
            log(f"네트워크 오류 (과목 {course}): {error_msg[:50]}...", True)

        # 세션 만료 감지
        if any(pattern in error_msg for pattern in ["HTTP Error 403", "HTTP Error 401", "권한이 없습니다", "로그인", "세션"]):
            SESSION["is_valid"] = False
            SESSION["token_validity"] = -1
            session_refresh_event.set()  # 세션 갱신 트리거
            log("🔑 세션 만료 감지, 갱신 요청 중...", True)

        # 서버 과부하 감지
        server_overload_patterns = ["timed out", "timeout", "HTTP Error 502", "HTTP Error 504",
                                    "HTTP Error 500", "Bad Gateway", "Gateway Time-out", "overloaded"]
        if any(pattern in error_msg.lower() for pattern in server_overload_patterns):
            SERVER_STATUS["is_overloaded"] = True
            SERVER_STATUS["consecutive_errors"] += 1
            # 10시 정각 피크 부하 감지
            now = datetime.now()
            if now.hour == 10 and now.minute == 0 and now.second < 30:
                SERVER_STATUS["peak_load_detected"] = True
                log(f"🔥 10시 정각 서버 과부하 감지! 연속 오류: {SERVER_STATUS['consecutive_errors']}", True)
            else:
                log(f"🔥 서버 과부하 감지! 연속 오류: {SERVER_STATUS['consecutive_errors']}", True)

        # 흰 화면 감지
        if "blank" in error_msg.lower() or "empty" in error_msg.lower():
            SERVER_STATUS["white_screen_detected"] = True
            log("⚠️ 흰 화면(빈 응답) 감지, 특수 처리 모드로 전환")

        # 재시도 로직
        if is_first_attempt:
            # 첫 시도 실패 시 즉시 재시도
            log(f"🔄 첫 시도 즉시 재시도...")
            # 세션 확인
            if not SESSION["is_valid"]:
                session_refresh_event.set()
                await asyncio.sleep(0.05)
            return await send_optimized_request(course, div, False)  # 일반 모드로 재시도

        return f"요청 실패: {error_msg[:30]}..."


def process_response(course, div, response):
    """응답 처리 함수"""
    # 응답 분석
    if "-3000" in response or "세션" in response or "로그인" in response:
        log(f"세션 만료 감지 (과목 {course})")
        SESSION["is_valid"] = False
        SESSION["token_validity"] = -1
        send_session_expired_notification(course)
        session_refresh_event.set()
        return False

    elif "초과" in response:
        log(f"인원 초과 (과목 {course})")
        return False

    elif "기간" in response:
        log(f"수강신청 기간 아님 (과목 {course})")
        send_mobile_alert("수강신청 기간이 아닙니다! 프로세스 정지")
        raise Exception("수강신청 기간이 아닙니다")

    elif "true" in response:
        log(f"🎉 수강신청 성공! (과목 {course}, 분반 {div})")
        send_success_notification(course, div)
        remove_subject(course)
        CONFIG["success_count"] += 1
        STATS["successes"] += 1
        return True

    elif not response or response.strip() == "":
        log(f"⚠️ 빈 응답 (흰 화면) 감지 (과목 {course})")
        SERVER_STATUS["white_screen_detected"] = True
        return False

    else:
        log(f"알 수 없는 응답 (과목 {course}): {response[:100]}...", True)
        # JSON 파싱 시도
        try:
            if "JSON" in response:
                json_data = json.loads(response)
                log(f"JSON 응답: {json_data}", True)
        except:
            pass
        return False


async def process_requests_with_interval(courses_to_process, is_first_attempt=False):
    """0.05초 간격으로 과목 요청 처리"""
    from subjects import priority_subjects

    # 우선순위 기반 요청 순서 결정
    if priority_subjects:
        # 우선순위 과목 먼저 처리
        prioritized_courses = []
        # 우선순위 과목 추가
        for course in priority_subjects:
            if course in courses_to_process:
                prioritized_courses.append((course, courses_to_process[course]))
        # 나머지 과목 추가
        for course, div in courses_to_process.items():
            if course not in priority_subjects:
                prioritized_courses.append((course, div))
    else:
        # 기존 순서 유지
        prioritized_courses = list(courses_to_process.items())

    # 전략 이름 로그
    strategy_name = "0.05초 간격 첫 시도 전략" if is_first_attempt else "일반 처리 모드"
    log(f"🚀 {strategy_name} 시작 ({len(prioritized_courses)}개 과목)")

    # 결과 저장
    results = {}

    # 첫 시도 0.05초 간격 전략
    if is_first_attempt:
        for i, (course, div) in enumerate(prioritized_courses):
            log(f"과목 {course} 요청 전송 중... ({i + 1}/{len(prioritized_courses)})")

            # 요청 전송
            response = await send_optimized_request(course, div, True)

            # 결과 저장 및 처리
            results[course] = {"response": response, "div": div}
            success = process_response(course, div, response)
            if success:
                log(f"✅ 과목 {course} 수강신청 성공!")

            # 마지막 과목이 아닐 경우만 간격 적용
            if i < len(prioritized_courses) - 1:
                # 0.04~0.06초 랜덤 간격 유지
                interval = CONFIG["SUBJECT_INTERVAL"] + random.uniform(
                    -CONFIG["SUBJECT_INTERVAL_JITTER"],
                    CONFIG["SUBJECT_INTERVAL_JITTER"]
                )
                await asyncio.sleep(interval)

    # 일반 모드 (매크로 탐지 방지)
    else:
        # 과부하 상태면 요청 제한
        if SERVER_STATUS["is_overloaded"]:
            log("⚠️ 서버 과부하 감지: 요청 수 제한")
            max_courses = min(CONFIG["MAX_THREADS"], len(prioritized_courses))
            prioritized_courses = prioritized_courses[:max_courses]

        # 순차적 처리
        for i, (course, div) in enumerate(prioritized_courses):
            # 이미 성공한 과목은 건너뜀
            if course not in courses_to_process:
                continue

            log(f"과목 {course} 요청 중... ({i + 1}/{len(prioritized_courses)})")

            # 세션 확인
            if not SESSION["is_valid"]:
                log("⚠️ 세션이 유효하지 않음, 갱신 요청")
                session_refresh_event.set()
                await asyncio.sleep(0.2)

            # 요청 전송 및 처리
            response = await send_optimized_request(course, div, False)
            results[course] = {"response": response, "div": div}
            success = process_response(course, div, response)

            # 매크로 탐지 방지 지연
            if i < len(prioritized_courses) - 1:
                if STATS["attempts"] <= 3:
                    delay = random.uniform(0.5, 1.0)  # 초기: 0.5-1초
                elif STATS["attempts"] <= 10:
                    delay = random.uniform(1.0, 2.0)  # 중간: 1-2초
                else:
                    delay = random.uniform(2.0, 3.0)  # 후기: 2-3초

                log(f"⏱️ 다음 과목까지 {delay:.2f}초 대기 (매크로 탐지 방지)", True)
                await asyncio.sleep(delay)

    return results