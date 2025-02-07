# notifier.py

import requests
from credentials import NTFY_TOPIC

def send_mobile_alert(message):
    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    try:
        response = requests.post(url, data=message.encode('utf-8'))
        if response.status_code == 200:
            print("휴대폰 알림 전송 성공")
        else:
            print("휴대폰 알림 전송 실패:", response.text)
    except Exception as e:
        print("알림 전송 중 오류 발생:", e)
