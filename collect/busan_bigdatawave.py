"""부산 Big-데이터웨이브(data.busan.go.kr)에서 보고서 관련 교통 자료를 받아 data/raw/busan_bigdatawave 에 저장.
상세 페이지의 파일 다운로드 링크(insertDownloadUtlz 'F'/'H')를 그대로 따라가며, 원본 해시·출처를 index.json 에 남긴다."""
import re, json, hashlib, os, sys, time, html, urllib.request, http.cookiejar, datetime, zipfile, io

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'raw', 'busan_bigdatawave')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130'
BASE = 'https://data.busan.go.kr'

DATASETS = {  # pk: 분류
 # 사고·안전
 '15114119': '사고·안전', '15061229': '사고·안전', '15034532': '사고·안전', '15164340': '사고·안전(API)', '15164350': '사고·안전(API)',
 # 고령·교통약자 이동
 '15061983': '고령·교통약자', '15128561': '고령·교통약자', '15147515': '고령·교통약자', '15028207': '고령·교통약자',
 # 대중교통 이용
 '15095329': '대중교통 이용', '15123610': '대중교통 이용', '3057229': '대중교통 이용', '15066704': '대중교통 이용', '15103328': '대중교통 이용',
 # 대중교통 공급(노선·정류소·차량)
 '15084251': '대중교통 공급', '15043689': '대중교통 공급', '15040508': '대중교통 공급(API)',
 '3078637': '마을버스(구군)', '3078955': '마을버스(구군)', '3079310': '마을버스(구군)', '3081589': '마을버스(구군)', '15006063': '마을버스(구군)',
 '15006179': '마을버스(구군)', '15025161': '마을버스(구군)', '15026985': '마을버스(구군)', '15053333': '마을버스(구군)', '15053836': '마을버스(구군)',
 '15116765': '마을버스(구군)', '3070497': '마을버스(구군)', '15053837': '시내버스(구군)', '15053334': '시내버스(구군)',
 # 자동차 의존
 '15063789': '자동차 등록',
}

cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.addheaders = [('User-Agent', UA)]

def get(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with op.open(req, timeout=120) as r:
        return r.read(), r.headers

def sniff(b):
    if b[:2] == b'PK': return 'zip/xlsx'
    if b[:4] == b'\xd0\xcf\x11\xe0': return 'xls(ole)'
    if b[:5] == b'%PDF-': return 'pdf'
    head = b[:600].lower()
    if b'<html' in head or b'<!doctype' in head: return 'HTML(오류)'
    return 'text'

def meta(s):
    t = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', s, flags=re.S)
    txt = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t)))
    def f(label):
        m = re.search(label + r'\s+(.{1,60}?)\s{1,}(?:원시시스템|관리부서|관리부서 전화번호|비용부과유무|제공형태|차기등록예정일|다운로드 횟수|키워드|$)', txt)
        return m.group(1).strip() if m else ''
    title = re.search(r'class="dataSetViewTitle"[^>]*>(.*?)<', s, re.S)
    lic = re.search(r'이용허락범위\s+(이용허락범위[^가-힣]*[가-힣 ]{2,20}?)\s', txt)
    upd = re.search(r'수정일\s+(\d{4}-\d{2}-\d{2})', txt)
    return {'title': html.unescape(title.group(1)).strip() if title else '', 'institution': f('제공기관'),
            'department': f('관리부서'), 'license': lic.group(1).strip() if lic else '', 'updated': upd.group(1) if upd else ''}

def safe(n):
    return re.sub(r'[\\/:*?"<>|]', '_', n).strip()

os.makedirs(ROOT, exist_ok=True)
get(BASE + '/bdip/')
idxp = os.path.join(ROOT, 'index.json')
index = json.load(open(idxp, encoding='utf-8')) if os.path.exists(idxp) else []
done = {(e['pk'], e['download_url']) for e in index if e.get('status') == 'ok'}
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec='seconds')

for pk, cat in DATASETS.items():
    durl = f'{BASE}/bdip/opendata/detail.do?publicdatapk={pk}'
    s = get(durl)[0].decode('utf-8', 'replace')
    m = meta(s)
    files = re.findall(r"insertDownloadUtlz\('type',\s*'%s',\s*'([FH])',\s*'([^']*)'\s*\+\s*'\.'\s*\+\s*'([^']*)',\s*'dDown',\s*'[^']*',\s*'([^']+)'\)" % pk, s)
    seen = set(); outs = []
    for ty, name, ext, url in files:
        url = html.unescape(url)
        if url in seen: continue
        seen.add(url); outs.append((name, ext, url))
    if not outs:
        print(pk, m['title'], '→ 파일 없음(API 전용)'); index.append({'pk': pk, 'category': cat, **m, 'detail_url': durl, 'status': 'no_file(api_only)', 'checked_at': now}); continue
    d = os.path.join(ROOT, safe(f"{pk}_{m['title'] or pk}"))
    os.makedirs(d, exist_ok=True)
    for name, ext, url in outs:
        if (pk, url) in done: continue
        try:
            b, h = get(url)
        except Exception as e:
            print('  실패', name, e); index.append({'pk': pk, 'category': cat, **m, 'detail_url': durl, 'download_url': url, 'status': f'error:{e}', 'checked_at': now}); continue
        kind = sniff(b)
        fn = safe(f'{name}.{ext.lower()}')
        if kind.startswith('HTML'):
            print('  HTML 응답(저장 안 함)', fn); index.append({'pk': pk, 'category': cat, **m, 'detail_url': durl, 'download_url': url, 'status': 'html_response', 'checked_at': now}); continue
        open(os.path.join(d, fn), 'wb').write(b)
        index.append({'pk': pk, 'category': cat, **m, 'detail_url': durl, 'download_url': url, 'file': os.path.relpath(os.path.join(d, fn), ROOT).replace('\\', '/'),
                      'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(), 'sniff': kind, 'status': 'ok', 'checked_at': now})
        print('  ok', pk, fn, len(b), kind)
        time.sleep(0.5)
    json.dump(index, open(idxp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(index, open(idxp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('done', sum(1 for e in index if e.get('status') == 'ok'), 'files')
