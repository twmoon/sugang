# main.py

import time
import random
from sugang_request import send_sugang_request
from notifier import send_mobile_alert
from subjects import subject_data

while True:
    try:
        # 모든 과목 수강신청 성공 시 종료
        if not subject_data:
            print("모든 학수번호 수강신청 성공! 종료합니다.")
            break

        # 등록된 모든 과목에 대해 수강신청 요청 전송
        for course, div in list(subject_data.items()):
            response_text = send_sugang_request(course, div)
            print(f"수강신청 요청 전송 - 학수번호: {course}, 분반: {div}")
            print(response_text)

            # 세션 만료 오류
            if "-3000" in response_text:
                send_mobile_alert("경고: 수강신청 서버 세션 만료")
            # 제한 인원 초과
            elif "초과" in response_text:
                send_mobile_alert("경고: 수강신청 제한 인원 초과")
            # 제한 인원 초과
            elif "기간" in response_text:
                send_mobile_alert("경고: 수강신청 기간 초과")
            # 요청 성공 (응답 문자열에 "true" 포함)
            elif "true" in response_text:
                send_mobile_alert(f"수강신청 성공!! (학수번호: {course}, 분반: {div})")
                print(f"수강신청 성공으로 {course} 제거합니다.")
                del subject_data[course]

            # 과목 간 랜덤 딜레이 (매크로 탐지 회피)
            time.sleep(random.randint(1, 5))

        # 다음 시도 전 남은 과목이 있다면 추가 대기
        if subject_data:
            random_delay = random.randint(10, 60)
            print(f"\n다음 시도까지 {random_delay}초 대기\n")
            time.sleep(random_delay)
    except Exception as e:
        print("요청 중 오류 발생:", e)
        time.sleep(1)
