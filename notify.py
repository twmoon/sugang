# 알림 기능 모듈

import requests
import threading
from utils import log
from config import CONFIG
from auth_config import NTFY_TOPIC

def send_mobile_alert(message, priority="high"):
    """메인 스레드 차단 없이 비동기로 알림 전송"""
    def _send_alert():
        url = f"https://ntfy.sh/{NTFY_TOPIC}"
        headers = {"Priority": priority}
        try:
            response = requests.post(url,
                                     data=message.encode('utf-8'),
                                     headers=headers,
                                     timeout=3)
            if response.status_code == 200:
                log(f"알림 전송 성공: {message}")
            else:
                log(f"알림 전송 실패: {response.text}")
        except Exception as e:
            log(f"알림 전송 오류: {e}", True)

    # 별도 스레드로 실행
    thread = threading.Thread(target=_send_alert)
    thread.daemon = True
    thread.start()


def send_success_notification(course, div):
    """수강신청 성공 알림"""
    message = f"🎉 수강신청 성공!! (과목: {course}, 분반: {div})"
    send_mobile_alert(message, "urgent")


def send_error_notification(error_message):
    """오류 발생 알림"""
    message = f"❌ 오류 발생: {error_message}"
    send_mobile_alert(message, "high")


def send_session_expired_notification(course=None):
    """세션 만료 알림"""
    course_info = f" ({course})" if course else ""
    message = f"세션 만료! 재로그인 중{course_info}"
    send_mobile_alert(message)


def send_start_notification(subject_list):
    """수강신청 시작 알림"""
    message = f"수강신청 프로세스 시작! 학수번호: {subject_list}"
    send_mobile_alert(message)


def send_completion_notification(success_count, elapsed_time):
    """수강신청 완료 알림"""
    message = f"✅ 수강신청 완료: {success_count}개 과목 등록 성공 (소요시간: {elapsed_time:.1f}초)"
    send_mobile_alert(message)