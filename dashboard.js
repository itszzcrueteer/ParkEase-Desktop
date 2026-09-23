/* ===================== STATE ===================== */

let systemActive = true;
let idCounter = 1000;

// Build parking spaces: Section A (32, full), Section B (24, 18 available),
// Section C (36), Section D (36) — total 128, occupancy target ~74% (95/128)
const SECTIONS = { A: 32, B: 24, C: 36, D: 36 };
let spaces = [];
(function buildSpaces() {
  Object.entries(SECTIONS).forEach(([sec, count]) => {
    for (let i = 1; i <= count; i++) {
      spaces.push({ id: `${sec}-${String(i).padStart(2, "0")}`, section: sec, status: "available" });
    }
  });
  // Section A: fill completely
  spaces.filter((s) => s.section === "A").forEach((s) => (s.status = "occupied"));
  // Section B: 18 available / 24 -> occupy 6
  spaces.filter((s) => s.section === "B").slice(0, 6).forEach((s) => (s.status = "occupied"));
  // Fill remaining sections until total occupied+reserved ~ 95, leaving a few reserved
  let occupiedCount = spaces.filter((s) => s.status !== "available").length;
  const targetOccupied = 95;
  const remaining = spaces.filter((s) => s.section === "C" || s.section === "D");
  let idx = 0;
  while (occupiedCount < targetOccupied - 3 && idx < remaining.length) {
    remaining[idx].status = "occupied";
    occupiedCount++;
    idx++;
  }
  // A few reserved (awaiting arrival) spaces
  for (let i = 0; i < 3 && idx < remaining.length; i++, idx++) {
    remaining[idx].status = "reserved";
  }
  // Make sure B-14, A-08, C-22, D-02, B-05 exist and match seed reservations below
})();

function findSpace(id) {
  return spaces.find((s) => s.id === id);
}

let reservations = [
  { id: idCounter++, user: "Alex Rivera", space: "B-14", time: "14:02", left: "04:12 left", status: "awaiting" },
  { id: idCounter++, user: "Jordan Lee", space: "A-08", time: "13:45", left: "", status: "confirmed" },
  { id: idCounter++, user: "Sam Chen", space: "C-22", time: "13:10", left: "", status: "confirmed" },
  { id: idCounter++, user: "Priya Nair", space: "D-11", time: "12:55", left: "", status: "confirmed" },
  { id: idCounter++, user: "Mark S.", space: "D-02", time: "11:30", left: "", status: "expired" },
  { id: idCounter++, user: "Lena Cruz", space: "C-04", time: "10:15", left: "", status: "cancelled" },
];
// keep referenced spaces consistent with statuses above
["B-14"].forEach((id) => (findSpace(id).status = "reserved"));
["A-08", "C-22", "D-11"].forEach((id) => (findSpace(id).status = "occupied"));
if (findSpace("D-02")) findSpace("D-02").status = "available";
if (findSpace("C-04")) findSpace("C-04").status = "available";
if (findSpace("B-05")) findSpace("B-05").status = "available";

let users = [
  { id: idCounter++, name: "Alex Rivera", role: "Driver", vehicle: "Honda Civic", flags: 0 },
  { id: idCounter++, name: "Jordan Lee", role: "Driver", vehicle: "Mazda 3", flags: 0 },
  { id: idCounter++, name: "Sam Chen", role: "Driver", vehicle: "Ford Focus", flags: 0 },
  { id: idCounter++, name: "Mark S.", role: "Driver", vehicle: "VW Golf", flags: 0 },
  { id: idCounter++, name: "Sarah", role: "Attendant", vehicle: "—", flags: 0 },
  { id: idCounter++, name: "Admin User", role: "Admin", vehicle: "—", flags: 0 },
];

let alerts = [
  {
    id: idCounter++,
    type: "warning",
    title: "Reservation Expired",
    text: "User 'Mark S.' failed to confirm Space D-02 within 5 mins.",
    time: "just now",
  },
  {
    id: idCounter++,
    type: "info",
    title: "Manual Release",
    text: "Space B-05 released by attendant 'Sarah'.",
    time: "2 mins ago",
  },
];

let history = [
  { time: "13:58", event: "Space B-05 released by attendant Sarah." },
  { time: "13:45", event: "Reservation confirmed for Jordan Lee — Space A-08." },
  { time: "13:10", event: "Reservation confirmed for Sam Chen — Space C-22." },
];

function addHistory(text) {
  const now = new Date();
  const time = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  history.unshift({ time, event: text });
  renderHistoryTable();
}

/* ===================== NAV ===================== */

document.querySelectorAll(".navitem").forEach((item) => {
  item.addEventListener("click", () => goTo(item.dataset.section));
});

function goTo(section) {
  document.querySelectorAll(".navitem").forEach((i) => i.classList.toggle("active", i.dataset.section === section));
  document.querySelectorAll("section.page").forEach((p) => p.classList.toggle("active", p.id === `page-${section}`));
}

/* ===================== TOAST ===================== */

function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("show"), 2200);
}

/* ===================== SYSTEM TOGGLE ===================== */

function toggleSystem() {
  systemActive = !systemActive;
  const pill = document.getElementById("systemPill");
  const text = document.getElementById("systemPillText");
  pill.classList.toggle("inactive", !systemActive);
  text.textContent = systemActive ? "System Active" : "System Paused";
  addHistory(`System status changed to ${systemActive ? "Active" : "Paused"} by Admin User.`);
}

/* ===================== RENDER: STATS ===================== */

function renderStats() {
  const total = spaces.length;
  const occupiedOrReserved = spaces.filter((s) => s.status !== "available").length;
  const pct = Math.round((occupiedOrReserved / total) * 100);
  document.getElementById("statOccPct").textContent = pct + "%";
  document.getElementById("statOccFrac").textContent = `${occupiedOrReserved}/${total} Spaces`;
  document.getElementById("statOccBar").style.width = pct + "%";

  const activeCount = reservations.filter((r) => r.status === "confirmed" || r.status === "awaiting").length;
  const awaitingCount = reservations.filter((r) => r.status === "awaiting").length;
  document.getElementById("statActive").textContent = activeCount;
  document.getElementById("statActiveNote").textContent = `${awaitingCount} awaiting arrival`;

  document.getElementById("statExpired").textContent = String(
    reservations.filter((r) => r.status === "expired").length
  ).padStart(2, "0");

  const totalFlags = users.reduce((sum, u) => sum + u.flags, 0);
  document.getElementById("statFlags").textContent = String(totalFlags).padStart(2, "0");
}

/* ===================== RENDER: RESERVATIONS TABLES ===================== */

function statusLabel(status) {
  return { confirmed: "Confirmed", awaiting: "Awaiting Arrival", expired: "Expired", cancelled: "Cancelled" }[status] || status;
}
function statusClass(status) {
  return { confirmed: "confirmed", awaiting: "awaiting", expired: "expired", cancelled: "cancelled" }[status] || "";
}

function reservationRowHTML(r) {
  const initials = r.user.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  const releaseBtn = r.status === "confirmed" || r.status === "awaiting"
    ? `<button class="link-action" onclick="releaseReservation(${r.id})">Release</button>`
    : `<span style="color:var(--faint);font-size:12.5px;">—</span>`;
  const manageBtn = `<button class="link-action" style="margin-left:10px;" onclick="openManage(${r.id})">Manage</button>`;
  return `<tr>
    <td><div class="userrow"><div class="avatar">${initials}</div> ${r.user}</div></td>
    <td>${r.space}</td>
    <td>${r.time}${r.left ? ` <span style="color:var(--faint);font-size:12px;">(${r.left})</span>` : ""}</td>
    <td><span class="status-pill ${statusClass(r.status)}">${statusLabel(r.status)}</span></td>
    <td>${releaseBtn}${manageBtn}</td>
  </tr>`;
}

function renderOverviewTable() {
  const filter = document.getElementById("overviewStatusFilter").value;
  let rows = reservations.filter((r) => r.status === "confirmed" || r.status === "awaiting");
  if (filter !== "all") rows = rows.filter((r) => r.status === filter);
  const body = document.getElementById("overviewTableBody");
  body.innerHTML = rows.length
    ? rows.map(reservationRowHTML).join("")
    : `<tr><td colspan="5" class="empty">No active reservations.</td></tr>`;
}

function renderReservationsTable() {
  const search = document.getElementById("resSearch").value.trim().toLowerCase();
  const filter = document.getElementById("resStatusFilter").value;
  let rows = reservations.slice();
  if (filter !== "all") rows = rows.filter((r) => r.status === filter);
  if (search) rows = rows.filter((r) => r.user.toLowerCase().includes(search) || r.space.toLowerCase().includes(search));
  const body = document.getElementById("reservationsTableBody");
  body.innerHTML = rows.length
    ? rows.map(reservationRowHTML).join("")
    : `<tr><td colspan="5" class="empty">No reservations match.</td></tr>`;
}

function releaseReservation(id) {
  const r = reservations.find((x) => x.id === id);
  if (!r) return;
  const sp = findSpace(r.space);
  if (sp) sp.status = "available";
  r.status = "cancelled";
  addHistory(`Space ${r.space} released — reservation for ${r.user} ended.`);
  toast(`Space ${r.space} released.`);
  renderAll();
}

/* ===================== MANAGE MODAL ===================== */

let manageTargetId = null;
function openManage(id) {
  const r = reservations.find((x) => x.id === id);
  if (!r) return;
  manageTargetId = id;
  document.getElementById("mgUser").value = r.user;
  document.getElementById("mgSpace").value = r.space;
  document.getElementById("mgStatus").value = r.status;
  openModal("manageModal");
}
function saveManage() {
  const r = reservations.find((x) => x.id === manageTargetId);
  if (!r) return;
  const newStatus = document.getElementById("mgStatus").value;
  const sp = findSpace(r.space);
  if (sp) {
    if (newStatus === "confirmed") sp.status = "occupied";
    else if (newStatus === "awaiting") sp.status = "reserved";
    else sp.status = "available";
  }
  r.status = newStatus;
  addHistory(`Reservation for ${r.user} (Space ${r.space}) updated to ${statusLabel(newStatus)}.`);
  toast("Reservation updated.");
  closeModal("manageModal");
  renderAll();
}

/* ===================== MANUAL ENTRY MODAL ===================== */

function openManualEntry() {
  const select = document.getElementById("meSpace");
  const available = spaces.filter((s) => s.status === "available");
  select.innerHTML = available.length
    ? available.map((s) => `<option value="${s.id}">${s.id}</option>`).join("")
    : `<option value="">No spaces available</option>`;
  document.getElementById("meUser").value = "";
  openModal("manualEntryModal");
}
function submitManualEntry() {
  const user = document.getElementById("meUser").value.trim();
  const spaceId = document.getElementById("meSpace").value;
  const status = document.getElementById("meStatus").value;
  if (!user || !spaceId) {
    toast("Enter a user name and pick a space.");
    return;
  }
  const now = new Date();
  const time = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  reservations.unshift({ id: idCounter++, user, space: spaceId, time, left: "", status });
  const sp = findSpace(spaceId);
  if (sp) sp.status = status === "confirmed" ? "occupied" : "reserved";
  addHistory(`Manual entry: ${user} assigned to Space ${spaceId} (${statusLabel(status)}).`);
  toast(`Reservation created for ${user}.`);
  closeModal("manualEntryModal");
  renderAll();
}

/* ===================== ALERTS ===================== */

function renderAlerts() {
  const list = document.getElementById("alertsList");
  if (!alerts.length) {
    list.innerHTML = `<p class="empty">No active alerts.</p>`;
    return;
  }
  list.innerHTML = alerts
    .map((a) => {
      const icon = a.type === "warning" ? "⚠️" : "ℹ️";
      const actions =
        a.type === "warning"
          ? `<div class="alert-actions">
               <button onclick="flagFromAlert(${a.id})">Flag User</button>
               <button onclick="dismissAlert(${a.id})">Dismiss</button>
             </div>`
          : `<div class="alert-time">${a.time}</div>`;
      return `<div class="alert-item">
        <div class="alert-ic ${a.type === "info" ? "info" : ""}">${icon}</div>
        <div>
          <div class="alert-title">${a.title}</div>
          <div class="alert-text">${a.text}</div>
          ${actions}
        </div>
      </div>`;
    })
    .join("");
}
function dismissAlert(id) {
  alerts = alerts.filter((a) => a.id !== id);
  renderAlerts();
  toast("Alert dismissed.");
}
function flagFromAlert(id) {
  const a = alerts.find((x) => x.id === id);
  if (!a) return;
  // pull the user name out of the alert text, e.g. "User 'Mark S.' failed..."
  const match = a.text.match(/'([^']+)'/);
  const name = match ? match[1] : "Unknown user";
  const user = users.find((u) => u.name === name);
  if (user) user.flags += 1;
  addHistory(`${name} flagged for review from reservation alert.`);
  dismissAlert(id);
  toast(`${name} flagged.`);
  renderAll();
}

/* ===================== SPACE MANAGEMENT SUMMARY ===================== */

function renderSpaceMgmt() {
  const list = document.getElementById("spaceMgmtList");
  list.innerHTML = Object.keys(SECTIONS)
    .map((sec) => {
      const secSpaces = spaces.filter((s) => s.section === sec);
      const available = secSpaces.filter((s) => s.status === "available").length;
      const total = secSpaces.length;
      const label = available === 0 ? `${total}/${total} Full` : `${available}/${total} Available`;
      return `<div class="space-row"><span>Section ${sec}</span><b>${label}</b></div>`;
    })
    .join("");
}

/* ===================== LIVE MAP ===================== */

function renderMap() {
  const container = document.getElementById("mapSections");
  container.innerHTML = Object.keys(SECTIONS)
    .map((sec) => {
      const secSpaces = spaces.filter((s) => s.section === sec);
      const cells = secSpaces
        .map(
          (s) =>
            `<div class="space-cell ${s.status}" title="${s.id} — ${s.status}" onclick="clickSpace('${s.id}')">${s.id.split("-")[1]}</div>`
        )
        .join("");
      return `<div class="map-section"><h4>Section ${sec}</h4><div class="space-grid">${cells}</div></div>`;
    })
    .join("");
}

function clickSpace(id) {
  const sp = findSpace(id);
  if (!sp) return;
  if (sp.status === "available") {
    if (confirm(`Space ${id} is available. Open Manual Entry to assign it?`)) {
      openManualEntry();
      setTimeout(() => (document.getElementById("meSpace").value = id), 0);
    }
  } else {
    const linkedRes = reservations.find((r) => r.space === id && (r.status === "confirmed" || r.status === "awaiting"));
    if (linkedRes && confirm(`Space ${id} is ${sp.status}, reserved by ${linkedRes.user}. Release it now?`)) {
      releaseReservation(linkedRes.id);
    } else if (!linkedRes && confirm(`Space ${id} is marked ${sp.status} with no linked reservation. Mark it available?`)) {
      sp.status = "available";
      addHistory(`Space ${id} manually marked available.`);
      renderAll();
    }
  }
}

/* ===================== USERS ===================== */

function renderUsersTable() {
  const search = document.getElementById("userSearch").value.trim().toLowerCase();
  let rows = users.slice();
  if (search) rows = rows.filter((u) => u.name.toLowerCase().includes(search));
  const body = document.getElementById("usersTableBody");
  body.innerHTML = rows.length
    ? rows
        .map((u) => {
          const initials = u.name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
          return `<tr>
            <td><div class="userrow"><div class="avatar">${initials}</div> ${u.name}</div></td>
            <td>${u.role}</td>
            <td>${u.vehicle}</td>
            <td>${u.flags > 0 ? `<span class="status-pill expired">${u.flags}</span>` : "—"}</td>
            <td><button class="link-action" onclick="removeUser(${u.id})">Remove</button></td>
          </tr>`;
        })
        .join("")
    : `<tr><td colspan="5" class="empty">No users match.</td></tr>`;
}
function removeUser(id) {
  const u = users.find((x) => x.id === id);
  if (!u) return;
  if (!confirm(`Remove ${u.name}?`)) return;
  users = users.filter((x) => x.id !== id);
  addHistory(`User ${u.name} removed by Admin User.`);
  renderAll();
}
function openUserModal() {
  document.getElementById("uName").value = "";
  document.getElementById("uVehicle").value = "";
  openModal("userModal");
}
function submitUser() {
  const name = document.getElementById("uName").value.trim();
  const role = document.getElementById("uRole").value;
  const vehicle = document.getElementById("uVehicle").value.trim() || "—";
  if (!name) {
    toast("Enter a name.");
    return;
  }
  users.push({ id: idCounter++, name, role, vehicle, flags: 0 });
  addHistory(`New ${role.toLowerCase()} added: ${name}.`);
  toast(`${name} added.`);
  closeModal("userModal");
  renderAll();
}

/* ===================== HISTORY ===================== */

function renderHistoryTable() {
  const body = document.getElementById("historyTableBody");
  body.innerHTML = history.length
    ? history.map((h) => `<tr><td style="white-space:nowrap;color:var(--faint);">${h.time}</td><td>${h.event}</td></tr>`).join("")
    : `<tr><td colspan="2" class="empty">No history yet.</td></tr>`;
}

/* ===================== CSV EXPORT ===================== */

function exportCSV() {
  const rows = [["User", "Space", "Reserved At", "Status"]];
  reservations.forEach((r) => rows.push([r.user, r.space, r.time, statusLabel(r.status)]));
  const csv = rows.map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "parkease-reservations.csv";
  a.click();
  URL.revokeObjectURL(url);
  toast("CSV exported.");
}

/* ===================== MODAL HELPERS ===================== */

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

/* ===================== RENDER ALL ===================== */

function renderAll() {
  renderStats();
  renderOverviewTable();
  renderReservationsTable();
  renderAlerts();
  renderSpaceMgmt();
  renderMap();
  renderUsersTable();
  renderHistoryTable();
}
renderAll();
