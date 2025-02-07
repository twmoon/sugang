# notifier.py
import requests
from credentials import PUSHOVER_TOKEN, PUSHOVER_USER_KEY

def send_mobile_alert(message):
    data = {
        "token": PUSHOVER_TOKEN,
        "user": PUSHOVER_USER_KEY,
        "message": message
    }
    try:
        r = requests.post("https://api.pushover.net/1/messages.json", data=data)
        if r.status_code == 200:
            print("휴대폰 알림 전송 성공")
        else:
            print("휴대폰 알림 전송 실패:", r.text)
    except Exception as e:
        print("알림 전송 중 오류 발생:", e)
