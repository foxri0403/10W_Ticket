# TicketRush

공연 티켓 예매 웹서비스

## 1. 프로젝트 소개

TicketRush는 콘서트, 공연, 페스티벌의 좌석을
예약할 수 있는 웹서비스입니다.

### 대상 사용자

- 콘서트와 공연을 예매하려는 사용자

## 2. 주요 기능

| 기능 | 설명 |
|---|---|
| 공연 목록 조회 | 공연 이름, 장소, 날짜, 가격 확인 |
| 예매 시간 확인 | 예매 시작 전 예약 차단 |
| 좌석 선택 | 공연별 선택 가능한 좌석 표시 및 이미 선택된 좌석 표시|
| 좌석 예약 | 닉네임으로 예약 |
| 예약 조회 | 예약 번호로 예매 정보 확인 |
| 예약 취소 | 예약을 취소하고 좌석 반환 |

## 3. 기술 스택

| 구분 | 기술 |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, FastAPI |
| Database | SQLite |
| Web Server | Nginx |
| Cloud | AWS EC2 |
| OS | Ubuntu 24.04 LTS |
| Version Control | GitHub |

## 4. AWS 아키텍처

사용자 브라우저
      |
      | HTTP :80
      v
AWS EC2 (Ubuntu 24.04)
      |
      v
Nginx :80
      |
      +---- / --------> HTML / CSS / JavaScript
      |
      +---- /api/ ----> FastAPI :8001
                             |
                             v
                         SQLite DB

## 5. 실행 및 배포
git clone https://github.com/foxri0403/10W_Ticket.git
cd 10W_Ticket
docker compose up -d --build
