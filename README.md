# 전기화재 예측 시스템
이 프로젝트는 기상 데이터와 전기 이상 신호를 분석하여 전기화재 위험을 예측하고,  
지도 기반 시각화를 통해 사용자에게 직관적인 위험 경보를 제공합니다.

##  주요 파일 설명
| 파일명 | 설명 |
|--------|------|
| `fire_risk.py` | 전기화재 예측을 위한 주요 분석 및 DB 연동 스크립트 |
| `index.html` | 지도 기반 시각화 웹 페이지 |
| `electric_alerts_with_coords.zip` | 경보 데이터 및 위치 정보 압축 파일 |

## 기술 스택
- Python (PyMySQL, Pandas 등)
- HTML + JavaScript (VWORLD 지도 연동)
- MySQL
- 기상청 단기예보 API
