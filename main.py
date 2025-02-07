# main__1.py
import time
import random
from sugang_request import send_sugang_request
from notifier import send_mobile_alert
from subjects import subject_data


while True:
    try:
        # 모든 과목에 대해 성공하면 종료
        if not subject_data:
            print("모든 학수번호 수강신청 성공! 종료합니다.")
            break

        # 학수번호로 수강신청 request 전송 (신청 완료된 과목 삭제)
        for course, div in list(subject_data.items()):
            response_text = send_sugang_request(course, div)
            print(f"수강신청 요청 전송 - 학수번호: {course}, 분반: {div}")
            print(response_text)

            # 오류 응답: 세션 만료(-3000 포함)인 경우 알림 전송
            if "-3000" in response_text:
                send_mobile_alert("경고: 수강신청 서버 세션 만료")
            # # 오류 응답: 해당 강좌 인원 초과 시 (-2000 포함)인 경우 알림 전송
            # elif "-2000" in response_text:
            #     send_mobile_alert("경고: 수강신청 제한 인원 초과")
            # 성공 응답 (응답 내 "true" 문자열 포함 시)
            elif "true" in response_text:
                send_mobile_alert(f"수강신청 성공!! (학수번호: {course}, 분반: {div})")
                print(f"수강신청 성공으로 {course} 제거합니다.")
                del subject_data[course]

            # 다음 항목 시도 전 랜덤 딜레이 (매크로 탐지 방지)
            time.sleep(random.randint(1, 5))

        # 한 사이클 완료 후, 남은 과목이 있다면 추가 대기 (매크로 탐지 방지)
        if subject_data:
            random_delay = random.randint(10, 60)
            print(f"\n다음 시도까지 {random_delay}초 대기\n")
            time.sleep(random_delay)
    except Exception as e:
        print("요청 중 오류 발생:", e)
        time.sleep(1)
