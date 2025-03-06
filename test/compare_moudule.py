"""
상명대학교 수강신청 세션 획득 성능 비교 테스트

다음 방식들의 성능을 비교합니다:
1. 기존 셀레니움 방식
2. Playwright 방식
3. Requests-HTML 방식
4. HTTPX + PyPpeteer 방식
5. MechanicalSoup 방식

먼저 필요한 패키지를 설치하세요:
pip install selenium webdriver-manager playwright requests-html pyppeteer httpx mechanicalsoup async-timeout

"""

import time
import asyncio
import urllib.request
import urllib.parse
import requests
import json
from datetime import datetime

# 기본 설정
CONFIG = {
    "ID": "202010861",
    "PW": "SmTlqkf99$",
    "DEBUG": True,
}

# 세션 상태 관리
SESSION = {
    "SGJSESSIONID": "",
    "WMONID": "",
    "is_valid": False,
}

# 로그 기록 함수
def log(message, is_debug=False):
    if is_debug and not CONFIG["DEBUG"]:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")

# 결과 저장 함수
def save_result(method, elapsed_time, success, tokens=None):
    result = {
        "method": method,
        "elapsed_time": elapsed_time,
        "success": success,
        "tokens": tokens if success else None
    }
    print(f"\n{'-'*50}")
    print(f"방식: {method}")
    print(f"성공 여부: {'성공' if success else '실패'}")
    print(f"소요 시간: {elapsed_time:.3f}초")
    if tokens:
        print(f"SGJSESSIONID: {tokens['SGJSESSIONID'][:10]}...")
        print(f"WMONID: {tokens['WMONID'][:10]}...")
    print(f"{'-'*50}\n")
    return result

# =============== 1. 기존 셀레니움 방식 ===============
def selenium_login():
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager

    log("셀레니움 방식 세션 획득 시작...")
    start_time = time.time()

    try:
        # 브라우저 설정
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")

        # 드라이버 초기화
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(10)

        tokens = {"SGJSESSIONID": "", "WMONID": ""}

        # 로그인 시도
        sso_url = "https://smsso.smu.ac.kr/svc/tk/Auth.do?ac=Y&RelayState=https%3A%2F%2Fsmsso.smu.ac.kr%2Fagree%2Fmain.jsp&ifa=N&id=sugang&"
        driver.get(sso_url)

        # 로그인 폼 채우기
        wait = WebDriverWait(driver, 5)
        username_field = wait.until(EC.presence_of_element_located((By.ID, "user_id")))
        password_field = driver.find_element(By.ID, "user_password")

        driver.execute_script("arguments[0].value = arguments[1]", username_field, CONFIG["ID"])
        driver.execute_script("arguments[0].value = arguments[1]", password_field, CONFIG["PW"])

        # 로그인 버튼 클릭
        driver.execute_script("doLogin();")

        # 세션 쿠키 획득 대기
        max_wait = 5
        start_wait = time.time()
        success = False

        while time.time() - start_wait < max_wait:
            cookies = driver.get_cookies()
            for cookie in cookies:
                if cookie['name'] == 'SGJSESSIONID':
                    tokens["SGJSESSIONID"] = cookie['value']
                elif cookie['name'] == 'WMONID':
                    tokens["WMONID"] = cookie['value']

            if tokens["SGJSESSIONID"] and tokens["WMONID"]:
                success = True
                break

            time.sleep(0.2)

        driver.quit()

        if success:
            elapsed_time = time.time() - start_time
            log(f"셀레니움 세션 획득 완료! ({elapsed_time:.3f}초)")
            return save_result("셀레니움", elapsed_time, True, tokens)
        else:
            elapsed_time = time.time() - start_time
            log(f"셀레니움 세션 획득 실패! ({elapsed_time:.3f}초)")
            return save_result("셀레니움", elapsed_time, False)

    except Exception as e:
        elapsed_time = time.time() - start_time
        log(f"셀레니움 오류: {str(e)}")
        return save_result("셀레니움", elapsed_time, False)

# =============== 2. Playwright 방식 ===============
async def playwright_login():
    from playwright.async_api import async_playwright

    log("Playwright 방식 세션 획득 시작...")
    start_time = time.time()

    try:
        async with async_playwright() as p:
            # 브라우저 설정 및 시작
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # 로그인 페이지 접속
            await page.goto("https://smsso.smu.ac.kr/svc/tk/Auth.do?ac=Y&RelayState=https%3A%2F%2Fsmsso.smu.ac.kr%2Fagree%2Fmain.jsp&ifa=N&id=sugang&")

            # 로그인 폼 채우기
            await page.fill('#user_id', CONFIG["ID"])
            await page.fill('#user_password', CONFIG["PW"])

            # 로그인 버튼 클릭
            await page.evaluate("doLogin();")

            # 리다이렉트 대기
            await page.wait_for_load_state('networkidle')

            # 쿠키 추출
            cookies = await context.cookies()
            tokens = {"SGJSESSIONID": "", "WMONID": ""}

            for cookie in cookies:
                if cookie['name'] == 'SGJSESSIONID':
                    tokens["SGJSESSIONID"] = cookie['value']
                elif cookie['name'] == 'WMONID':
                    tokens["WMONID"] = cookie['value']

            await browser.close()

            success = bool(tokens["SGJSESSIONID"] and tokens["WMONID"])
            elapsed_time = time.time() - start_time

            if success:
                log(f"Playwright 세션 획득 완료! ({elapsed_time:.3f}초)")
            else:
                log(f"Playwright 세션 획득 실패! ({elapsed_time:.3f}초)")

            return save_result("Playwright", elapsed_time, success, tokens if success else None)

    except Exception as e:
        elapsed_time = time.time() - start_time
        log(f"Playwright 오류: {str(e)}")
        return save_result("Playwright", elapsed_time, False)

# =============== 3. Requests-HTML 방식 ===============
async def requests_html_login():
    from requests_html import AsyncHTMLSession

    log("Requests-HTML 방식 세션 획득 시작...")
    start_time = time.time()

    try:
        # 비동기 세션 생성
        session = AsyncHTMLSession()

        # 로그인 페이지 접속
        r = await session.get("https://smsso.smu.ac.kr/svc/tk/Auth.do?ac=Y&RelayState=https%3A%2F%2Fsmsso.smu.ac.kr%2Fagree%2Fmain.jsp&ifa=N&id=sugang&")

        # 자바스크립트 렌더링 - 비동기 버전
        await r.html.arender(sleep=1)

        # 로그인 폼 채우기 및 제출
        script = f"""
        document.getElementById('user_id').value = '{CONFIG["ID"]}';
        document.getElementById('user_password').value = '{CONFIG["PW"]}';
        doLogin();
        """
        await r.html.arender(script=script, sleep=3)

        # 쿠키 추출
        tokens = {"SGJSESSIONID": "", "WMONID": ""}
        for cookie in session.cookies:
            if cookie.name == 'SGJSESSIONID':
                tokens["SGJSESSIONID"] = cookie.value
            elif cookie.name == 'WMONID':
                tokens["WMONID"] = cookie.value

        await session.close()

        success = bool(tokens["SGJSESSIONID"] and tokens["WMONID"])
        elapsed_time = time.time() - start_time

        if success:
            log(f"Requests-HTML 세션 획득 완료! ({elapsed_time:.3f}초)")
        else:
            log(f"Requests-HTML 세션 획득 실패! ({elapsed_time:.3f}초)")

        return save_result("Requests-HTML", elapsed_time, success, tokens if success else None)

    except Exception as e:
        elapsed_time = time.time() - start_time
        log(f"Requests-HTML 오류: {str(e)}")
        return save_result("Requests-HTML", elapsed_time, False)

# =============== 4. HTTPX + PyPpeteer 방식 ===============
async def httpx_pyppeteer_login():
    import httpx
    from pyppeteer import launch

    log("HTTPX + PyPpeteer 방식 세션 획득 시작...")
    start_time = time.time()

    try:
        # PyPpeteer로 브라우저 시작
        browser = await launch(headless=True, args=['--no-sandbox'])
        page = await browser.newPage()

        # 로그인 페이지 접속
        await page.goto("https://smsso.smu.ac.kr/svc/tk/Auth.do?ac=Y&RelayState=https%3A%2F%2Fsmsso.smu.ac.kr%2Fagree%2Fmain.jsp&ifa=N&id=sugang&")

        # 로그인 폼 채우기
        await page.type('#user_id', CONFIG["ID"])
        await page.type('#user_password', CONFIG["PW"])

        # 로그인 버튼 클릭
        await page.evaluate("doLogin();")

        # 페이지 로딩 대기
        await asyncio.sleep(2)

        # 쿠키 추출
        cookies = await page.cookies()
        tokens = {"SGJSESSIONID": "", "WMONID": ""}

        for cookie in cookies:
            if cookie['name'] == 'SGJSESSIONID':
                tokens["SGJSESSIONID"] = cookie['value']
            elif cookie['name'] == 'WMONID':
                tokens["WMONID"] = cookie['value']

        await browser.close()

        # 토큰 획득 후 HTTPX로 세션 유효성 확인
        if tokens["SGJSESSIONID"] and tokens["WMONID"]:
            async with httpx.AsyncClient() as client:
                headers = {
                    'Host': 'sugang.smu.ac.kr',
                    'Cookie': f'WMONID={tokens["WMONID"]}; SGJSESSIONID={tokens["SGJSESSIONID"]}',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                }

                response = await client.head(
                    'https://sugang.smu.ac.kr/index.do',
                    headers=headers,
                    timeout=2
                )

                success = response.status_code == 200
        else:
            success = False

        elapsed_time = time.time() - start_time

        if success:
            log(f"HTTPX + PyPpeteer 세션 획득 완료! ({elapsed_time:.3f}초)")
        else:
            log(f"HTTPX + PyPpeteer 세션 획득 실패! ({elapsed_time:.3f}초)")

        return save_result("HTTPX + PyPpeteer", elapsed_time, success, tokens if success else None)

    except Exception as e:
        elapsed_time = time.time() - start_time
        log(f"HTTPX + PyPpeteer 오류: {str(e)}")
        return save_result("HTTPX + PyPpeteer", elapsed_time, False)

# =============== 5. MechanicalSoup 방식 ===============
def mechanicalsoup_login():
    import mechanicalsoup

    log("MechanicalSoup 방식 세션 획득 시작...")
    start_time = time.time()

    try:
        browser = mechanicalsoup.StatefulBrowser()

        # 로그인 페이지 접속
        browser.open("https://smsso.smu.ac.kr/svc/tk/Auth.do?ac=Y&RelayState=https%3A%2F%2Fsmsso.smu.ac.kr%2Fagree%2Fmain.jsp&ifa=N&id=sugang&")

        # 자바스크립트 로그인 폼 제출 시도 (직접적인 JS 실행은 지원하지 않음)
        # 대신 HTML 폼 제출 시도
        browser.select_form('form[name="form"]')
        browser["user_id"] = CONFIG["ID"]
        browser["user_password"] = CONFIG["PW"]

        # 폼 제출 시도
        browser.submit_selected()

        # 쿠키 추출
        tokens = {"SGJSESSIONID": "", "WMONID": ""}
        for cookie in browser.session.cookies:
            if cookie.name == 'SGJSESSIONID':
                tokens["SGJSESSIONID"] = cookie.value
            elif cookie.name == 'WMONID':
                tokens["WMONID"] = cookie.value

        success = bool(tokens["SGJSESSIONID"] and tokens["WMONID"])
        elapsed_time = time.time() - start_time

        if success:
            log(f"MechanicalSoup 세션 획득 완료! ({elapsed_time:.3f}초)")
        else:
            log(f"MechanicalSoup 세션 획득 실패! ({elapsed_time:.3f}초)")

        return save_result("MechanicalSoup", elapsed_time, success, tokens if success else None)

    except Exception as e:
        elapsed_time = time.time() - start_time
        log(f"MechanicalSoup 오류: {str(e)}")
        return save_result("MechanicalSoup", elapsed_time, False)

# =============== 성능 비교 메인 함수 ===============
async def compare_login_methods():
    print("\n" + "="*50)
    print("상명대학교 로그인 세션 획득 성능 비교")
    print("="*50)

    results = []

    # 1. 셀레니움 방식
    results.append(selenium_login())

    # 2. Playwright 방식 (비동기)
    results.append(await playwright_login())

    # 3. Requests-HTML 방식 (비동기로 변경)
    results.append(await requests_html_login())

    # 4. HTTPX + PyPpeteer 방식 (비동기)
    results.append(await httpx_pyppeteer_login())

    # 5. MechanicalSoup 방식
    results.append(mechanicalsoup_login())

    # 결과 정렬 및 출력
    print("\n" + "="*50)
    print("결과 요약 (성능순 정렬)")
    print("="*50)

    # 성공한 방식만 추출하고 시간순 정렬
    successful_results = [r for r in results if r["success"]]
    successful_results.sort(key=lambda x: x["elapsed_time"])

    # 실패한 방식 추출
    failed_results = [r for r in results if not r["success"]]

    # 성공한 방식 결과 출력
    for i, result in enumerate(successful_results, 1):
        print(f"{i}. {result['method']}: {result['elapsed_time']:.3f}초")

    # 실패한 방식 출력
    if failed_results:
        print("\n실패한 방식:")
        for result in failed_results:
            print(f"- {result['method']}")

    print("\n가장 빠른 방식:", successful_results[0]["method"] if successful_results else "없음")

    return successful_results[0] if successful_results else None

# 실행 함수
def main():
    asyncio.run(compare_login_methods())

if __name__ == "__main__":
    main()