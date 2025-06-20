import pandas as pd
import json
import pymysql
import math

# MySQL 연결
conn = pymysql.connect(
    host='localhost',
    user='root',
    password='tl737373',
    db='power_monitor',
    charset='utf8mb4'
)
print("DB 연결 성공")

# 데이터 불러오기 
df = pd.read_sql("SELECT * FROM alerts_with_weather_fixed", conn)
conn.close()

# 전송값 파싱 (전류/전압)
def parse_json(js):
    try:
        val = json.loads(js)
        return pd.Series({
            '전압_c': val['v']['c'],
            '전압_m': val['v']['m'],
            '전류_c': val['c']['c'],
            '전류_m': val['c']['m']
        })
    except:
        return pd.Series({'전압_c': None, '전압_m': None, '전류_c': None, '전류_m': None})

df = pd.concat([df, df['전송값'].apply(parse_json)], axis=1)

# 날짜 및 계절 처리
df['수신일자'] = pd.to_datetime(df['수신일자'])
df['month'] = df['수신일자'].dt.month

def get_season(month):
    if month in [12, 1, 2]: return '겨울'
    elif month in [3, 4, 5]: return '봄'
    elif month in [6, 7, 8]: return '여름'
    else: return '가을'

df['season'] = df['month'].apply(get_season)

cols_to_float = ['기온', '이슬점', '습도', '풍속', '측정값', '위도', '경도']
for col in cols_to_float:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# 기준값 정의 (계절별 위험 요소 판단 기준)
season_rules = {
    '봄':   {'기온': 18.0, '이슬점': 13.0, '습도': 78},
    '여름': {'기온': 26.0, '이슬점': 23.0, '습도': 85},
    '가을': {'풍속': 2.5, '이슬점': 1.5, '습도': 73},
    '겨울': {'기온': 3.5, '이슬점': 0.0, '습도': 75}
}


def evaluate_risk_and_color(row):
    season = row.get('season')
    rule = season_rules.get(season, {})
    flags = {
        '기온': False,
        '이슬점': False,
        '습도': False,
        '풍속': False
    }

    # 계절별 조건 충족 여부 판단
    if season == '봄':
        flags['기온'] = row['기온'] <= rule['기온']
        flags['이슬점'] = row['이슬점'] >= rule['이슬점']
        flags['습도'] = row['습도'] >= rule['습도']
    elif season == '여름':
        flags['기온'] = row['기온'] <= rule['기온']
        flags['이슬점'] = row['이슬점'] >= rule['이슬점']
        flags['습도'] = row['습도'] >= rule['습도']
    elif season == '가을':
        flags['풍속'] = row['풍속'] >= rule['풍속']
        flags['이슬점'] = row['이슬점'] >= rule['이슬점']
        flags['습도'] = row['습도'] >= rule['습도']
    elif season == '겨울':
        flags['기온'] = row['기온'] <= rule['기온']
        flags['이슬점'] = row['이슬점'] <= rule['이슬점']
        flags['습도'] = row['습도'] >= rule['습도']

    # 위험요소 텍스트 결정
    risk_conditions = []
    if season == '봄':
        if flags['이슬점']: risk_conditions.append('이슬점↑')
        if flags['습도']:   risk_conditions.append('습도↑')
        if flags['기온']:   risk_conditions.append('기온↓')
    elif season == '여름':
        if flags['습도']:   risk_conditions.append('습도↑')
        if flags['이슬점']: risk_conditions.append('이슬점↑')
        if flags['기온']:   risk_conditions.append('기온↓')
    elif season == '가을':
        if flags['풍속']:   risk_conditions.append('풍속↑')
        if flags['이슬점']: risk_conditions.append('이슬점↑')
        if flags['습도']:   risk_conditions.append('습도↑')
    elif season == '겨울':
        if flags['기온']:   risk_conditions.append('기온↓')
        if flags['이슬점']: risk_conditions.append('이슬점↓')
        if flags['습도']:   risk_conditions.append('습도↑')

    risk_text = '정상' if not risk_conditions else ', '.join(risk_conditions)


    weather_risk_count = sum(flags.values())

    # 전기 경보 여부 판단
    signal = str(row['이상신호'])
    try:
        value = float(row['측정값'])
    except:
        value = 0

    elec_abnormal = ('누설전류' in signal and value >= 10) or (signal == '과전류' and value >= 20)

    # 색상 판단
    if elec_abnormal and weather_risk_count >= 1:
        color = '빨간색'
    elif elec_abnormal and weather_risk_count == 0:
        color = '주황색'
    elif not elec_abnormal and weather_risk_count == 3:
        color = '노란색'
    elif weather_risk_count <= 2:
        color = '초록색'
        risk_text = '정상'

    return pd.Series({
        '위험요소': risk_text,
        '경보발생': elec_abnormal,
        '색상': color
    })

df[['위험요소', '경보발생', '색상']] = df.apply(evaluate_risk_and_color, axis=1)

def safe_str(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "정보 없음"
    # 수치일 경우 소수 2자리로 표시
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


# GeoJSON 변환
geo_df = df[['수신일자', '장치번호', '이상신호', '측정값', '위험요소', '경보발생', '위도', '경도','기온', '풍속', '습도', '이슬점', '색상' ]]
features = []

for _, row in geo_df.iterrows():
    try:
        lat = float(str(row['위도']).strip())
        lon = float(str(row['경도']).strip())
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": {
                "경보 일시": safe_str(row['수신일자']),
                "장치번호": safe_str(row['장치번호']),
                "이상신호": safe_str(row['이상신호']),
                "측정값": safe_str(row['측정값']),
                "위험요소": safe_str(row['위험요소']),
                "경보발생": safe_str(row['경보발생']),
                "이슬점": safe_str(row.get('이슬점', '')),
                "습도": safe_str(row.get('습도', '')),
                "기온": safe_str(row.get('기온', '')),
                "풍속": safe_str(row.get('풍속', '')),
                "색상": safe_str(row.get('색상', '')) 
            }
        })
    except Exception as e:
        print(f"좌표 변환 실패 → 위도: {row['위도']}, 경도: {row['경도']} | 에러: {e}")
        continue

    
geojson = {
    "type": "FeatureCollection",
    "features": features
}

with open("electric_alerts_with_coords.geojson", "w", encoding="utf-8") as f:
    json.dump(geojson, f, ensure_ascii=False, indent=2)

print("electric_alerts_with_coords.geojson 생성 완료") 