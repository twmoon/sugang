# sugang_request.py
import urllib.request
import urllib.parse
from credentials import SGJSESSIONID, WMONID

HEADERS = {
    'Host': 'sugang.smu.ac.kr',
    'Cookie': f'WMONID={WMONID}; SGJSESSIONID={SGJSESSIONID}',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0',
    'Accept': '*/*',
    'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://sugang.smu.ac.kr/index.do',
    'X-Requested-With': 'XMLHttpRequest',
    'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
    'Origin': 'https://sugang.smu.ac.kr'
}

def send_sugang_request(course, div):
    data = {
        '_AUTH_MENU_KEY': '',
        '@d1#strCampusRcd': 'CMN001.0001',
        '@d1#strSbjNo': course,          # 학수번호
        '@d1#strDivcls': str(div),        # 분반
        '@d#': '@d1#',
        '@d1#': 'dmParamTlsnAplyDirect',
        '@d1#tp': 'dm'
    }
    data_encoded = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(
        url='https://sugang.smu.ac.kr/UcrTlsn/tlsnAplyDirect.do',
        data=data_encoded,
        headers=HEADERS,
        method='POST'
    )
    with urllib.request.urlopen(req) as response:
        return response.read().decode('utf-8')
