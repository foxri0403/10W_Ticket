import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="TicketRush API", version="1.0.0")

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "ticketrush.db"
KST = ZoneInfo("Asia/Seoul")
SEATS = [f"{row}{number}" for row in "ABCD" for number in range(1, 6)]


def now():
    return datetime.now(KST)


@contextmanager
def database():
    connection = sqlite3.connect(str(DB_PATH), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=10000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with database() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                venue TEXT NOT NULL,
                event_date TEXT NOT NULL,
                booking_open TEXT NOT NULL,
                price INTEGER NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                event_id INTEGER NOT NULL,
                seat TEXT NOT NULL,
                nickname TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY(event_id) REFERENCES events(id)
            )
        """)

        db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            unique_active_seat
            ON reservations(event_id, seat)
            WHERE status = 'active'
        """)

        count = db.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]

        if count == 0:
            current = now()

            events = [
                (
                    1, "2026 LIVE CONCERT", "서울 공연장",
                    (current + timedelta(days=14)).isoformat(),
                    (current - timedelta(days=1)).isoformat(),
                    50000
                ),
                (
                    2, "ROCK FESTIVAL", "부산 공연장",
                    (current + timedelta(days=21)).isoformat(),
                    (current + timedelta(days=1)).isoformat(),
                    65000
                ),
                (
                    3, "WINTER CLASSIC", "서울 공연장",
                    (current + timedelta(days=30)).isoformat(),
                    (current - timedelta(days=1)).isoformat(),
                    40000
                )
            ]

            db.executemany(
                """INSERT INTO events
                (id, title, venue, event_date, booking_open, price)
                VALUES (?, ?, ?, ?, ?, ?)""",
                events
            )


initialize_database()


class ReservationRequest(BaseModel):
    event_id: int
    seat: str
    nickname: str = Field(min_length=1, max_length=30)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "TicketRush"}


@app.get("/api/events")
def get_events():
    with database() as db:
        events = db.execute(
            "SELECT * FROM events ORDER BY id"
        ).fetchall()

    return [
        {
            **dict(event),
            "booking_available": now() >=
                datetime.fromisoformat(event["booking_open"])
        }
        for event in events
    ]


@app.get("/api/events/{event_id}/seats")
def get_seats(event_id: int):
    with database() as db:
        event = db.execute(
            "SELECT id FROM events WHERE id = ?",
            (event_id,)
        ).fetchone()

        if event is None:
            raise HTTPException(404, "공연을 찾을 수 없습니다.")

        rows = db.execute(
            """SELECT seat FROM reservations
               WHERE event_id = ? AND status = 'active'""",
            (event_id,)
        ).fetchall()

    reserved = {row["seat"] for row in rows}

    return {
        "event_id": event_id,
        "seats": [
            {
                "seat": seat,
                "available": seat not in reserved
            }
            for seat in SEATS
        ]
    }


@app.post("/api/reservations", status_code=201)
def create_reservation(request: ReservationRequest):
    seat = request.seat.strip().upper()
    nickname = request.nickname.strip()

    if seat not in SEATS:
        raise HTTPException(400, "올바르지 않은 좌석입니다.")

    if not nickname:
        raise HTTPException(400, "닉네임을 입력하세요.")

    try:
        with database() as db:
            db.execute("BEGIN IMMEDIATE")

            event = db.execute(
                "SELECT * FROM events WHERE id = ?",
                (request.event_id,)
            ).fetchone()

            if event is None:
                raise HTTPException(404, "공연을 찾을 수 없습니다.")

            if now() < datetime.fromisoformat(event["booking_open"]):
                raise HTTPException(403, "예매 시작 전입니다.")

            code = secrets.token_urlsafe(24)

            db.execute(
                """INSERT INTO reservations
                (code, event_id, seat, nickname, status, created_at)
                VALUES (?, ?, ?, ?, 'active', ?)""",
                (
                    code, request.event_id, seat,
                    nickname, now().isoformat()
                )
            )

    except sqlite3.IntegrityError:
        raise HTTPException(409, "이미 예약된 좌석입니다.")
    except sqlite3.OperationalError:
        raise HTTPException(503, "예약 요청이 많습니다. 다시 시도하세요.")

    return {
        "message": "예약 성공",
        "reservation_code": code,
        "event_id": request.event_id,
        "seat": seat,
        "nickname": nickname
    }


@app.get("/api/reservations/{code}")
def get_reservation(code: str):
    with database() as db:
        reservation = db.execute(
            """SELECT r.code, r.event_id, r.seat,
                      r.nickname, r.status, r.created_at,
                      e.title, e.price
               FROM reservations r
               JOIN events e ON e.id = r.event_id
               WHERE r.code = ?""",
            (code,)
        ).fetchone()

    if reservation is None:
        raise HTTPException(404, "예약을 찾을 수 없습니다.")

    return dict(reservation)


@app.delete("/api/reservations/{code}")
def cancel_reservation(code: str):
    with database() as db:
        db.execute("BEGIN IMMEDIATE")

        result = db.execute(
            """UPDATE reservations
               SET status = 'cancelled'
               WHERE code = ? AND status = 'active'""",
            (code,)
        )

        if result.rowcount == 0:
            raise HTTPException(
                404, "유효한 예약을 찾을 수 없습니다."
            )

    return {"message": "예약이 취소되었습니다.", "code": code}
