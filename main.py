import requests
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

# GitHub Secrets 정보추출
SERVICE_KEY = os.environ['DATA_API_KEY']
EMAIL_USER = os.environ['EMAIL_USER']
EMAIL_PW = os.environ['EMAIL_PW']

def get_bids():
    url = "http://apis.data.go.kr/1230000/BidPublicInfoService05/getBidPblancListInfoCnstwk01"
    
    # 전송시 시간과 １시간전 시간 대조
    now = datetime.now() + timedelta(hours=9) # GitHub 서버는 UTC 기준이라 한국시간(+9)으로 보정
    one_hour_ago = now - timedelta(hours=1, minutes=5) # 5분 여유를 두어 누락 방지
    
    today_str = now.strftime('%Y%m%d')
    
    params = {
        'serviceKey': SERVICE_KEY,
        'type': 'json',
        'bidNtceDt': today_str,
        'numOfRows': '300', # 넉넉하게 조회
        'inqryDiv': '1'     # 공고일자 기준 조회
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        items = data.get('response', {}).get('body', {}).get('items', [])
        if not items: return []
    except Exception as e:
        print(f"API 호출 오류: {e}")
        return []
    
    matched = []
    for item in items:
        # 1. 업종코드 0037 확인 (필요시 상세조회 API 연동 가능하나 보통 공사목록에서 필터링 가능)
        # 2. 공고 시간 확인 (최근 1시간 내 등록된 것만)
        ntce_dt_str = item.get('bidNtceDt', '') # 예: "2026-03-25 14:00"
        try:
            ntce_dt = datetime.strptime(ntce_dt_str, '%Y-%m-%d %H:%M')
            if not (one_hour_ago <= ntce_dt <= now):
                continue # 1시간 이전 공고는 스킵 (중복 방지)
        except:
            continue

        title = item.get('bidNtceNm', '')
        price = int(item.get('presmptPrce', 0)) if item.get('presmptPrce') else 0
        area = item.get('rgstRtlimitCn', '') # 지역제한내용
        
        # 3. 필터링 조건 적용 (2억 미만, 수의 제외, 세종/무제한)
        if price < 200000000 and "수의" not in title:
            # 지역 조건: '세종' 포함 혹은 '제한없음' 혹은 '전국'
            if any(region in area for region in ["세종", "제한없음", "전국"]) or not area:
                link = item.get('bidNtceDtlUrl', '#')
                matched.append(f"📌 [신규] {title}\n💰 추정가격: {price:,}원\n📍 지역제한: {area}\n⏰ 공고시간: {ntce_dt_str}\n🔗 링크: {link}")
                
    return matched

def send_mail(contents):
    if not contents:
        print("조건에 맞는 신규 공고가 없습니다.")
        return
        
    body = "\n\n" + "\n\n---\n\n".join(contents)
    msg = MIMEText(body)
    msg['Subject'] = f"🔔 [전기공사 0037] 신규 입찰 알림 ({datetime.now().strftime('%H:%M')})"
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PW)
        smtp.send_message(msg)
        print(f"{len(contents)}건의 공고를 메일로 전송했습니다.")

if __name__ == "__main__":
    send_mail(get_bids())
