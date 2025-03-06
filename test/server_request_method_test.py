import requests
import time
import statistics
from tabulate import tabulate



def test_request_methods(url, test_count=10):
    """HEAD와 GET 요청의 속도를 여러 번 테스트하여 비교합니다."""
    print(f"서버 요청 방식 속도 비교 테스트: {url}")
    print(f"테스트 횟수: {test_count}회\n")

    # 결과 저장용 리스트
    head_times = []
    get_times = []
    results = []

    # 공통 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Connection': 'keep-alive'
    }

    try:
        # 여러 번 테스트 수행
        for i in range(test_count):
            print(f"테스트 #{i + 1} 실행 중...")

            # HEAD 요청 테스트
            try:
                start_time = time.time()
                head_response = requests.head(
                    url,
                    headers=headers,
                    timeout=5,
                    allow_redirects=False
                )
                head_time = (time.time() - start_time) * 1000  # 밀리초로 변환
                head_status = head_response.status_code
                head_headers_count = len(head_response.headers)
                head_times.append(head_time)
            except Exception as e:
                print(f"HEAD 요청 오류: {e}")
                head_time = None
                head_status = "오류"
                head_headers_count = 0

            # 잠시 대기 (서버 부하 방지)
            time.sleep(0.5)

            # GET 요청 테스트
            try:
                start_time = time.time()
                get_response = requests.get(
                    url,
                    headers=headers,
                    timeout=5,
                    allow_redirects=False,
                    stream=True  # 응답 본문 크기 비교를 위해 스트림 모드 사용
                )
                get_time = (time.time() - start_time) * 1000  # 밀리초로 변환

                # 응답 본문 크기 계산 (스트림 모드에서)
                content_size = 0
                for chunk in get_response.iter_content(chunk_size=1024):
                    content_size += len(chunk)

                get_status = get_response.status_code
                get_headers_count = len(get_response.headers)
                get_times.append(get_time)
            except Exception as e:
                print(f"GET 요청 오류: {e}")
                get_time = None
                get_status = "오류"
                get_headers_count = 0
                content_size = 0

            # 결과 저장
            faster = "HEAD" if head_time and get_time and head_time < get_time else "GET" if head_time and get_time else "-"
            diff = abs(head_time - get_time) if head_time and get_time else None
            results.append({
                "테스트 #": i + 1,
                "HEAD 상태": head_status,
                "HEAD 시간(ms)": round(head_time, 2) if head_time else None,
                "GET 상태": get_status,
                "GET 시간(ms)": round(get_time, 2) if get_time else None,
                "더 빠른 방식": faster,
                "시간차(ms)": round(diff, 2) if diff else None
            })

            # 잠시 대기 (서버 부하 방지)
            time.sleep(1.0)

        # 결과 테이블 출력
        print("\n" + "=" * 50)
        print("테스트 결과 상세")
        print("=" * 50)
        print(tabulate(results, headers="keys", tablefmt="grid"))

        # 통계 분석
        valid_head_times = [t for t in head_times if t is not None]
        valid_get_times = [t for t in get_times if t is not None]

        if valid_head_times and valid_get_times:
            head_avg = statistics.mean(valid_head_times)
            get_avg = statistics.mean(valid_get_times)

            head_median = statistics.median(valid_head_times)
            get_median = statistics.median(valid_get_times)

            try:
                head_stdev = statistics.stdev(valid_head_times)
                get_stdev = statistics.stdev(valid_get_times)
            except:
                head_stdev = 0
                get_stdev = 0

            faster_count = sum(1 for r in results if r["더 빠른 방식"] == "HEAD")
            slower_count = sum(1 for r in results if r["더 빠른 방식"] == "GET")

            print("\n" + "=" * 50)
            print("통계 분석")
            print("=" * 50)
            stats_table = [
                ["평균 응답 시간(ms)", round(head_avg, 2), round(get_avg, 2), "HEAD" if head_avg < get_avg else "GET",
                 round(abs(head_avg - get_avg), 2)],
                ["중앙값(ms)", round(head_median, 2), round(get_median, 2), "HEAD" if head_median < get_median else "GET",
                 round(abs(head_median - get_median), 2)],
                ["표준 편차(ms)", round(head_stdev, 2), round(get_stdev, 2), "-", "-"],
                ["가장 빨랐던 횟수", faster_count, slower_count, "HEAD" if faster_count > slower_count else "GET",
                 abs(faster_count - slower_count)]
            ]
            print(tabulate(stats_table, headers=["통계", "HEAD", "GET", "우세", "차이"], tablefmt="grid"))

            # 최종 결론
            print("\n" + "=" * 50)
            print("최종 결론")
            print("=" * 50)
            if head_avg < get_avg:
                print(f"✅ HEAD 요청이 평균 {round(get_avg - head_avg, 2)}ms 더 빠릅니다.")
                recommendation = "세션 확인에 HEAD 요청을 사용하는 것이 효율적입니다."
            else:
                print(f"📊 GET 요청이 평균 {round(head_avg - get_avg, 2)}ms 더 빠릅니다.")
                recommendation = "세션 확인에 stream=True 옵션을 사용한 GET 요청을 고려해보세요."

            if abs(head_avg - get_avg) < 10:
                print("⚠️ 두 방식의 차이가 10ms 미만으로 큰 차이가 없습니다.")
                recommendation += " 다만 차이가 크지 않으므로 다른 요소도 함께 고려하세요."

            print(f"💡 권장사항: {recommendation}")


    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")


if __name__ == "__main__":
    # 테스트할 URL
    url = "https://sugang.smu.ac.kr/index.do"  # 상명대학교 수강신청 시스템 URL

    # 10회 테스트 실행
    test_request_methods(url, test_count=10)