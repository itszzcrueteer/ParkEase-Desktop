/* ===================== GREETING ===================== */

(function setGreeting() {
  const hour = new Date().getHours();
  const part = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
  document.getElementById("greeting").textContent = `Good ${part}, Daniel`;
})();

/* ===================== STATE ===================== */

let reservation = {
  garage: "Metro Central Garage",
  address: "420 Market St, San Francisco · Zone B",
  space: "B-14",
  starts: "09:00",
  ends: "14:30",
  rate: 4.5,
  status: "confirmed", // confirmed -> arrived
  endTime: Date.now() + (1 * 60 * 60 * 1000 + 24 * 60 * 1000 + 55 * 1000), // ~01:24:55 from load
};

let vehicles = [
  { id: 1, label: "Honda Civic · Silver", plate: "7KLM-294", type: "Gas", primary: true },
  { id: 2, label: "Tesla Model 3", plate: "8RNP-102", type: "EV", primary: false },
];

let activity = [
  { id: 1, place: "Bayview Marina Lot", date: "Oct 28", duration: "3h 15m", hours: 3.25, spot: "Space A-07", price: 14.63 },
  { id: 2, place: "SFO Terminal 2 Garage", date: "Oct 25", duration: "6h 40m", hours: 6.67, spot: "Space C-22", price: 30.4 },
  { id: 3, place: "Mission District Street", date: "Oct 22", duration: "1h 50m", hours: 1.83, spot: "Meter 114", price: 6.0 },
  { id: 4, place: "Metro Central Garage", date: "Oct 18", duration: "5h 05m", hours: 5.08, spot: "Space B-09", price: 22.85 },
];

let notifications = [
  { id: 1, text: "Your reservation at Metro Central Garage starts soon.", time: "10m ago" },
  { id: 2, text: "Receipt available for your Oct 25 session at SFO Terminal 2.", time: "2d ago" },
];

const TOTAL_SPACES = 48;
let lot = [];
(function buildLot() {
  const yourIndex = 14; // matches "15" label in the wireframe (1-indexed 15th cell)
  for (let i = 1; i <= TOTAL_SPACES; i++) {
    let status = "free";
    if (i - 1 === yourIndex) status = "yours";
    else if (Math.random() < 0.55) status = "occupied";
    lot.push({ num: String(i).padStart(2, "0"), status });
  }
})();

/* ===================== NAV ===================== */

document.querySelectorAll(".navitem").forEach((item) => {
  item.addEventListener("click", () => goTo(item.dataset.section));
});
function goTo(section) {
  document.querySelectorAll(".navitem").forEach((i) => i.classList.toggle("active", i.dataset.section === section));
  document.querySelectorAll("section.page").forEach((p) => p.classList.toggle("active", p.id === `page-${section}`));
}

/* ===================== TOAST / MODALS ===================== */

function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("show"), 2200);
}
function openModal(id) {
  document.getElementById(id).classList.add("show");
}
function closeModal(id) {
  document.getElementById(id).classList.remove("show");
}
document.querySelectorAll(".modal-overlay").forEach((ov) => {
  ov.addEventListener("click", (e) => {
    if (e.target === ov) ov.classList.remove("show");
  });
});

/* ===================== DROPDOWNS ===================== */

function toggleDropdown(id) {
  const el = document.getElementById(id);
  const wasOpen = el.classList.contains("show");
  document.querySelectorAll(".dropdown").forEach((d) => d.classList.remove("show"));
  if (!wasOpen) {
    el.classList.add("show");
    if (id === "bellDropdown") {
      document.getElementById("bellDot").style.display = "none";
      renderBell();
    }
  }
}
document.addEventListener("click", (e) => {
  if (!e.target.closest(".bell") && !e.target.closest(".user-chip") && !e.target.closest(".dropdown")) {
    document.querySelectorAll(".dropdown").forEach((d) => d.classList.remove("show"));
  }
});
function renderBell() {
  const el = document.getElementById("bellDropdown");
  el.innerHTML = notifications.length
    ? notifications.map((n) => `<div class="ddi"><b style="font-weight:600;">${n.text}</b><br><span style="color:var(--faint);font-size:11.5px;">${n.time}</span></div>`).join("")
    : `<div class="ddi muted">No new notifications.</div>`;
}

/* ===================== COUNTDOWN ===================== */

function formatRemaining(ms) {
  if (ms <= 0) return "00:00:00";
  const totalSec = Math.floor(ms / 1000);
  const h = String(Math.floor(totalSec / 3600)).padStart(2, "0");
  const m = String(Math.floor((totalSec % 3600) / 60)).padStart(2, "0");
  const s = String(totalSec % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}
function tickCountdown() {
  const remaining = reservation.endTime - Date.now();
  document.getElementById("timeRemaining").textContent = formatRemaining(remaining);
  if (remaining <= 0) {
    document.getElementById("timeRemaining").textContent = "Expired";
  }
}
setInterval(tickCountdown, 1000);

function extendReservation() {
  reservation.endTime += 30 * 60 * 1000; // +30 min
  const endDate = new Date(reservation.endTime);
  reservation.ends = endDate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  document.getElementById("resEnds").textContent = reservation.ends;
  toast("Reservation extended by 30 minutes.");
  tickCountdown();
}

function confirmArrival() {
  if (reservation.status === "arrived") return;
  reservation.status = "arrived";
  const pill = document.getElementById("resStatusPill");
  pill.innerHTML = `<span class="dot"></span> Arrived`;
  const btn = document.getElementById("confirmArrivalBtn");
  btn.disabled = true;
  btn.textContent = "Arrival confirmed";
  toast("Arrival confirmed — enjoy your stay!");
}

/* ===================== LIVE MAP ===================== */

function renderLot() {
  const grid = document.getElementById("lotGrid");
  const free = lot.filter((c) => c.status === "free").length;
  document.getElementById("mapSummary").textContent = `${reservation.garage} · ${free} of ${TOTAL_SPACES} spaces free`;
  document.getElementById("yourSpaceLabel").textContent = reservation.space;
  grid.innerHTML = lot
    .map(
      (c) =>
        `<div class="space-cell ${c.status}" onclick="clickSpace('${c.num}','${c.status}')">${c.status === "yours" ? "" : c.num}</div>`
    )
    .join("");
}

function clickSpace(num, status) {
  if (status === "occupied") return;
  if (status === "yours") {
    toast(`Space ${reservation.space} is your active reservation.`);
    return;
  }
  document.getElementById("spaceModalTitle").textContent = `Space ${num}`;
  document.getElementById("spaceModalSub").textContent = `${reservation.garage} · Lot A, Section B — Available now`;
  document.getElementById("spaceModal").dataset.space = num;
  openModal("spaceModal");
}
function reserveFromMap() {
  const num = document.getElementById("spaceModal").dataset.space;
  toast(`Reservation request sent for space ${num}.`);
  closeModal("spaceModal");
}

/* ===================== VEHICLES ===================== */

function vehicleIcon(v) {
  return v.type === "EV" ? "🔋" : "🚗";
}

function renderVehicles() {
  const primary = vehicles.find((v) => v.primary) || vehicles[0];
  const others = vehicles.filter((v) => v !== primary);

  document.getElementById("primaryVehicleBox").innerHTML = primary
    ? `<div class="vehicle-row">
        <div class="vehicle-ic">${vehicleIcon(primary)}</div>
        <div><b>${primary.label}</b><span>Plate ${primary.plate}</span></div>
      </div>`
    : `<p style="color:var(--faint);font-size:13px;">No primary vehicle yet.</p>`;

  document.getElementById("otherVehiclesBox").innerHTML = others
    .map(
      (v) => `<div class="vehicle-row">
        <div class="vehicle-ic">${vehicleIcon(v)}</div>
        <div><b>${v.label}</b><span>${v.type} · ${v.plate}</span></div>
        <button class="rm" onclick="removeVehicle(${v.id})">Remove</button>
      </div>`
    )
    .join("");

  document.getElementById("allVehiclesList").innerHTML = vehicles
    .map(
      (v) => `<div class="vehicle-row">
        <div class="vehicle-ic">${vehicleIcon(v)}</div>
        <div><b>${v.label}${v.primary ? " (Primary)" : ""}</b><span>${v.type} · Plate ${v.plate}</span></div>
        ${v.primary ? "" : `<button class="rm" onclick="setPrimary(${v.id})" style="margin-left:auto;margin-right:10px;">Set primary</button>`}
        <button class="rm" onclick="removeVehicle(${v.id})">Remove</button>
      </div>`
    )
    .join("");
}
function removeVehicle(id) {
  const v = vehicles.find((x) => x.id === id);
  if (!v) return;
  if (!confirm(`Remove ${v.label}?`)) return;
  vehicles = vehicles.filter((x) => x.id !== id);
  if (v.primary && vehicles.length) vehicles[0].primary = true;
  toast(`${v.label} removed.`);
  renderVehicles();
}
function setPrimary(id) {
  vehicles.forEach((v) => (v.primary = v.id === id));
  renderVehicles();
  toast("Primary vehicle updated.");
}
function submitVehicle() {
  const makeModel = document.getElementById("vMakeModel").value.trim();
  const plate = document.getElementById("vPlate").value.trim();
  const type = document.getElementById("vType").value;
  if (!makeModel || !plate) {
    toast("Enter a make/model and plate.");
    return;
  }
  vehicles.push({ id: Date.now(), label: makeModel, plate, type, primary: vehicles.length === 0 });
  document.getElementById("vMakeModel").value = "";
  document.getElementById("vPlate").value = "";
  toast(`${makeModel} added.`);
  closeModal("vehicleModal");
  renderVehicles();
}

/* ===================== ACTIVITY / HISTORY / STATS ===================== */

function renderActivity() {
  const list = document.getElementById("recentActivityList");
  list.innerHTML = activity
    .slice(0, 3)
    .map(
      (a) => `<div class="activity-row">
        <div class="activity-check">✓</div>
        <div><b>${a.place}</b><span>${a.date} · ${a.duration} · ${a.spot}</span></div>
        <div class="activity-price">$${a.price.toFixed(2)}</div>
      </div>`
    )
    .join("");

  const body = document.getElementById("historyTableBody");
  body.innerHTML = activity
    .map(
      (a) => `<tr>
        <td>${a.place}</td><td>${a.date}</td><td>${a.duration}</td><td>${a.spot}</td><td>$${a.price.toFixed(2)}</td>
      </tr>`
    )
    .join("");
}

function renderStats() {
  const sessions = activity.length;
  const hours = activity.reduce((s, a) => s + a.hours, 0);
  const spent = activity.reduce((s, a) => s + a.price, 0);
  const avg = sessions ? spent / sessions : 0;
  document.getElementById("statSessions").textContent = sessions;
  document.getElementById("statHours").textContent = hours.toFixed(1);
  document.getElementById("statSpent").textContent = "$" + spent.toFixed(2);
  document.getElementById("statAvg").textContent = "$" + avg.toFixed(2);
}

/* ===================== SETTINGS ===================== */

function saveSettings() {
  const name = document.getElementById("setName").value.trim();
  if (name) {
    document.querySelector(".user-chip .name").textContent = name;
    document.getElementById("greeting").textContent = document.getElementById("greeting").textContent.replace(/,\s*\w+$/, ", " + name.split(" ")[0]);
  }
  toast("Settings saved.");
}

/* ===================== SUPPORT ===================== */

function submitSupport() {
  const msg = document.getElementById("supportMsg").value.trim();
  if (!msg) {
    toast("Type a message first.");
    return;
  }
  document.getElementById("supportMsg").value = "";
  closeModal("supportModal");
  toast("Support request sent — we'll follow up by email.");
}

/* ===================== INIT ===================== */

renderLot();
renderVehicles();
renderActivity();
renderStats();
renderBell();
tickCountdown();
