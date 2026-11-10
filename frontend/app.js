const $ = id => document.getElementById(id);
const money = value => Number(value).toLocaleString("ko-KR") + "원";

let events = [];
let selectedEvent = null;
let selectedSeat = null;
let toastTimer = null;

function notify(message) {
  const element = $("toast");
  element.textContent = message;
  element.style.display = "block";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => element.style.display = "none", 4500);
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "요청 처리에 실패했습니다."
    );
  }
  return data;
}

async function loadEvents() {
  try {
    events = await request("/api/events");
    const grid = $("eventGrid");
    grid.replaceChildren();

    const symbols = ["🎤", "🎸", "🎻"];

    for (const [index, event] of events.entries()) {
      const card = document.createElement("article");
      card.className = "event-card";

      const banner = document.createElement("div");
      banner.className = `event-banner banner-${index % 3 + 1}`;
      banner.textContent = symbols[index % 3];

      const body = document.createElement("div");
      body.className = "event-body";

      const status = document.createElement("div");
      status.className = event.booking_available ? "status" : "status soon";
      status.textContent = event.booking_available ? "● 예매 가능" : "● 오픈 예정";

      const title = document.createElement("h3");
      title.textContent = event.title;

      const venue = document.createElement("p");
      venue.textContent =
        `${new Date(event.event_date).toLocaleDateString("ko-KR")} · ${event.venue}`;

      const price = document.createElement("div");
      price.className = "event-price";
      price.textContent = money(event.price);

      const button = document.createElement("button");
      button.className = "primary-button full";
      button.textContent = event.booking_available ? "좌석 선택하기" : "예매 시작 전";
      button.disabled = !event.booking_available;
      button.addEventListener("click", () => openBooking(event));

      body.append(status, title, venue, price, button);
      card.append(banner, body);
      grid.append(card);
    }
  } catch (error) {
    $("eventGrid").textContent = "공연 조회 실패: " + error.message;
  }
}

async function openBooking(event) {
  selectedEvent = event;
  selectedSeat = null;
  $("bookingTitle").textContent = event.title + " · 좌석 선택";
  $("summaryEvent").textContent = event.title;
  $("bookingSection").classList.remove("hidden");
  updateSummary();
  await loadSeats();
  $("bookingSection").scrollIntoView({behavior:"smooth"});
}

async function loadSeats() {
  if (!selectedEvent) return;

  try {
    const data = await request(`/api/events/${selectedEvent.id}/seats`);
    const grid = $("seatGrid");
    grid.replaceChildren();

    const selectedStillAvailable = data.seats.some(
      seat => seat.seat === selectedSeat && seat.available
    );
    if (!selectedStillAvailable) selectedSeat = null;

    for (const seat of data.seats) {
      const button = document.createElement("button");
      button.textContent = seat.seat;
      button.className =
        "seat" + (seat.seat === selectedSeat ? " selected" : "");
      button.disabled = !seat.available;
      button.setAttribute(
        "aria-label",
        `${seat.seat} ${seat.available ? "예약 가능" : "예약 완료"}`
      );

      button.addEventListener("click", () => {
        selectedSeat = seat.seat === selectedSeat ? null : seat.seat;
        updateSummary();
        loadSeats();
      });

      grid.append(button);
    }
    updateSummary();
  } catch(error) {
    notify(error.message);
  }
}

function updateSummary() {
  $("summarySeat").textContent = selectedSeat || "미선택";
  $("summaryPrice").textContent =
    selectedSeat && selectedEvent ? money(selectedEvent.price) : "0원";
  $("reserveButton").disabled = !selectedSeat;
}

async function reserve() {
  if (!selectedEvent || !selectedSeat) {
    notify("좌석을 선택하세요.");
    return;
  }

  const nickname = $("nickname").value.trim();

  if (!nickname) {
    notify("닉네임을 입력하세요.");
    return;
  }

  const button = $("reserveButton");
  button.disabled = true;

  try {
    const result = await request("/api/reservations", {
      method: "POST",
      body: JSON.stringify({
        event_id: selectedEvent.id,
        seat: selectedSeat,
        nickname
      })
    });

    localStorage.setItem("ticketrush_last_code", result.reservation_code);
    $("reservationCode").value = result.reservation_code;
    notify("예매 성공! 예약 번호를 안전하게 보관하세요.");

    await loadSeats();
    openMyBookings();
    await lookupReservation();

  } catch(error) {
    notify(error.message);
    await loadSeats();
  } finally {
    updateSummary();
  }
}

function openMyBookings() {
  $("reservationSection").classList.remove("hidden");
  $("reservationCode").value =
    $("reservationCode").value ||
    localStorage.getItem("ticketrush_last_code") ||
    "";
  $("reservationSection").scrollIntoView({behavior:"smooth"});
}

async function lookupReservation() {
  const code = $("reservationCode").value.trim();
  const details = $("reservationDetails");
  details.replaceChildren();

  if (!code) {
    notify("예약 번호를 입력하세요.");
    return;
  }

  try {
    const data = await request(
      `/api/reservations/${encodeURIComponent(code)}`
    );

    const heading = document.createElement("h3");
    heading.textContent = data.title;

    const info = document.createElement("p");
    info.textContent =
      `예매자: ${data.nickname} | 좌석: ${data.seat} | ` +
      `가격: ${money(data.price)} | ` +
      `상태: ${data.status === "active" ? "예약 완료" : "취소됨"}`;

    const codeText = document.createElement("p");
    codeText.textContent = "예약 번호: " + data.code;

    details.append(heading, info, codeText);

    if (data.status === "active") {
      const cancel = document.createElement("button");
      cancel.className = "outline-button";
      cancel.textContent = "예매 취소";

      cancel.addEventListener("click", async () => {
        if (!confirm("정말 예매를 취소하시겠습니까?")) return;
        cancel.disabled = true;

        try {
          await request(
            `/api/reservations/${encodeURIComponent(code)}`,
            {method:"DELETE"}
          );

          notify("예매가 취소되었습니다.");
          await lookupReservation();
          await loadSeats();
        } catch(error) {
          notify(error.message);
          cancel.disabled = false;
        }
      });

      details.append(cancel);
    }
  } catch(error) {
    details.textContent = error.message;
  }
}

$("myBookings").addEventListener("click", openMyBookings);
$("refreshSeats").addEventListener("click", loadSeats);
$("reserveButton").addEventListener("click", reserve);
$("lookupButton").addEventListener("click", lookupReservation);

loadEvents();
