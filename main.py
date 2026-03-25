import requests
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

# 보안 정보
SERVICE_KEY = os.environ['DATA_API_KEY']
EMAIL_USER = os.environ['EMAIL_USER']
EMAIL_PW = os.environ['EMAIL_PW']

def get_bids():
    url = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoCnstwk01"
    
    # 한국 시간 기준 설정
    now_kst = datetime.utcnow() + timedelta(hours=9)
    # 넉넉하게 '최근 70분' 이내 공고를 다 가져오도록 설정 (실행 지연 대비)
    check_start_time = now_kst - timedelta(minutes=70)
    
    today_str = now_kst.strftime('%Y%m%d')
    
    params = {
        'serviceKey': SERVICE_KEY,
        'type': 'json',
        'bidNtceDt': today_str,
        'numOfRows': '500', 
        'inqryDiv': '1'
    }

    try:
        response = requests.get(url, params=params)
        # 만약 API 키 문제라면 여기서 에러 메시지가 출력됩니다.
        if response.status_code != 200:
            print(f"API 연결 실패: {response.status_code}")
            return []
        
        items = response.json().get('response', {}).get('body', {}).get('items', [])
        if not items: return []
    except Exception as e:
        print(f"오류 발생: {e}")
        return []
    
    matched = []
    for item in items:
        # 공고 등록 시간 파싱
        ntce_dt_str = item.get('bidNtceDt', '') 
        try:
            ntce_dt = datetime.strptime(ntce_dt_str, '%Y-%m-%d %H:%M')
            # [핵심] 최근 70분 이내에 등록된 공고인가?
            if not (check_start_time <= ntce_dt <= now_kst):
                continue
        except:
            continue

        title = item.get('bidNtceNm', '')
        price = int(item.get('presmptPrce', 0)) if item.get('presmptPrce') else 0
        area = item.get('rgstRtlimitCn', '')
        
        # 필터링 조건 (90억 및 지역/수의 조건)
        if price < 9000000000 and "수의" not in title:
            if any(region in area for region in ["세종", "제한없음", "전국"]) or not area:
                link = item.get('bidNtceDtlUrl', '#')
                matched.append(f"📌 [신규] {title}\n💰 가격: {price:,}원\n📍 지역: {area}\n⏰ 등록시간: {ntce_dt_str}\n🔗 링크: {link}")
                
    return matched

def send_mail(contents):
    if not contents:
        print("최근 1시간 내에 올라온 신규 공고가 없습니다.")
        return
        
    body = "\n\n" + "\n\n---\n\n".join(contents)
    msg = MIMEText(body)
    msg['Subject'] = f"🔔 [전기공사] 신규 공고 알림 ({datetime.now().strftime('%H:%M')})"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PW)
        smtp.send_message(msg)
        print(f"메일 발송 성공: {len(contents)}건")

if __name__ == "__main__":
    send_mail(get_bids())
