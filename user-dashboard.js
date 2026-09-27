
/*  API CONFIG  */

// Use app-config.js if it defines API_BASE_URL.
// Otherwise, use the local Flask server.
const API_ROOT = (
  typeof API_BASE_URL !== "undefined"
    ? API_BASE_URL
    : "http://127.0.0.1:5001"
)
  .replace(/\/+$/, "")
  .replace(/\/api$/, "");

const TOTAL_SPACES = 48;

function getSavedUser() {
  const saved =
    localStorage.getItem("parkease_user") ||
    sessionStorage.getItem("parkease_user");

  try {
    return saved ? JSON.parse(saved) : null;
  } catch {
    return null;
  }
}

function getToken() {
  return (
    localStorage.getItem("parkease_token") ||
    sessionStorage.getItem("parkease_token")
  );
}

async function apiRequest(path, options = {}) {
  const headers = {
    ...(options.headers || {}),
  };

  const token = getToken();

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  if (options.body) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_ROOT}${path}`, {
    ...options,
    headers,
  });

  let data = {};

  try {
    data = await response.json();
  } catch {
    // Some responses may not contain JSON.
  }

  if (!response.ok) {
    throw new Error(data.message || `Request failed (${response.status})`);
  }

  return data;
}

/* ===================== GREETING / PROFILE ===================== */

(function setGreeting() {
  const user = getSavedUser();
  const hour = new Date().getHours();

  const part =
    hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";

  const firstName = user?.firstName || "User";
  const lastName = user?.lastName || "";
  const fullName = [firstName, lastName].filter(Boolean).join(" ");

  const initials = [firstName, lastName]
    .filter(Boolean)
    .map((name) => name[0].toUpperCase())
    .join("");

  const profileName = document.getElementById("profileName");
  const profileInitials = document.getElementById("profileInitials");
  const profileRole = document.getElementById("profileRole");
  const greeting = document.getElementById("greeting");

  if (profileName) profileName.textContent = fullName;
  if (profileInitials) profileInitials.textContent = initials;

  if (profileRole) {
    profileRole.textContent =
      user?.role === "admin" ? "Administrator" : "Regular User";
  }

  if (greeting) {
    greeting.textContent = `Good ${part}, ${firstName}`;
  }
})();

/* ===================== STATE ===================== */

// No fake reservation is assigned automatically.
let reservation = null;

// These remain empty until vehicle/history APIs are connected.
let vehicles = [];
let activity = [];
let notifications = [];

let lot = [];

/* ===================== NAVIGATION ===================== */

document.querySelectorAll(".navitem").forEach((item) => {
  item.addEventListener("click", () => goTo(item.dataset.section));
});

function goTo(section) {
  document.querySelectorAll(".navitem").forEach((item) => {
    item.classList.toggle("active", item.dataset.section === section);
  });

  document.querySelectorAll("section.page").forEach((page) => {
    page.classList.toggle("active", page.id === `page-${section}`);
  });
}

/* ===================== TOAST / MODALS ===================== */

function toast(message) {
  const element = document.getElementById("toast");
  if (!element) return;

  element.textContent = message;
  element.classList.add("show");

  clearTimeout(element._timer);

  element._timer = setTimeout(() => {
    element.classList.remove("show");
  }, 2500);
}

function openModal(id) {
  document.getElementById(id)?.classList.add("show");
}

function closeModal(id) {
  document.getElementById(id)?.classList.remove("show");
}

document.querySelectorAll(".modal-overlay").forEach((overlay) => {
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) {
      overlay.classList.remove("show");
    }
  });
});

/* ===================== DROPDOWNS ===================== */

function toggleDropdown(id) {
  const element = document.getElementById(id);
  if (!element) return;

  const wasOpen = element.classList.contains("show");

  document.querySelectorAll(".dropdown").forEach((dropdown) => {
    dropdown.classList.remove("show");
  });

  if (!wasOpen) {
    element.classList.add("show");

    if (id === "bellDropdown") {
      const dot = document.getElementById("bellDot");
      if (dot) dot.style.display = "none";

      renderBell();
    }
  }
}

document.addEventListener("click", (event) => {
  if (
    !event.target.closest(".bell") &&
    !event.target.closest(".user-chip") &&
    !event.target.closest(".dropdown")
  ) {
    document.querySelectorAll(".dropdown").forEach((dropdown) => {
      dropdown.classList.remove("show");
    });
  }
});

function renderBell() {
  const element = document.getElementById("bellDropdown");
  if (!element) return;

  element.innerHTML = notifications.length
    ? notifications
        .map(
          (notification) => `
            <div class="ddi">
              <b style="font-weight:600;">${notification.text}</b>
              <br>
              <span style="color:var(--faint);font-size:11.5px;">
                ${notification.time}
              </span>
            </div>
          `
        )
        .join("")
    : `<div class="ddi muted">No new notifications.</div>`;
}

/* ===================== RESERVATION CARD ===================== */

function findReservationCard() {
  const statusPill = document.getElementById("resStatusPill");

  if (statusPill) {
    let element = statusPill;

    while (element && element !== document.body) {
      if (
        element.classList?.contains("card") ||
        element.classList?.contains("reservation-card") ||
        element.classList?.contains("panel")
      ) {
        return element;
      }

      element = element.parentElement;
    }
  }

  // Fallback: locate the "ACTIVE RESERVATION" heading and move upward.
  const heading = [...document.querySelectorAll("*")].find(
    (element) =>
      element.children.length === 0 &&
      element.textContent.trim().toUpperCase() === "ACTIVE RESERVATION"
  );

  if (!heading) return null;

  let element = heading;

  for (let i = 0; i < 6 && element; i++) {
    if (element.contains(statusPill)) return element;
    element = element.parentElement;
  }

  return heading.parentElement?.parentElement || null;
}

function updateReservationCard() {
  const card = findReservationCard();
  const arrivalButton = document.getElementById("confirmArrivalBtn");

  // Regular users must not confirm their own arrival.
  if (arrivalButton) {
    arrivalButton.style.display = "none";
  }

  if (!reservation) {
    if (card) card.style.display = "none";
    return;
  }

  if (card) card.style.display = "";

  const statusPill = document.getElementById("resStatusPill");
  if (statusPill) {
    const statusLabels = {
      pending: "Pending approval",
      approved: "Approved",
      arrived: "Arrived",
    };

    statusPill.innerHTML =
      `<span class="dot"></span> ${statusLabels[reservation.status] || reservation.status}`;
  }

  const spaceElement = document.getElementById("resSpace");
  if (spaceElement) {
    spaceElement.textContent = reservation.spaceNumber;
  }

  const yourSpaceLabel = document.getElementById("yourSpaceLabel");
  if (yourSpaceLabel) {
    yourSpaceLabel.textContent = reservation.spaceNumber;
  }

  const timeRemaining = document.getElementById("timeRemaining");
  if (timeRemaining) {
    timeRemaining.textContent =
      reservation.status === "pending"
        ? "Waiting for admin approval"
        : reservation.status === "approved"
          ? "Approved — waiting for arrival"
          : "Arrival confirmed";
  }
}

async function loadActiveReservation() {
  try {
    const data = await apiRequest("/api/reservations/active");
    reservation = data.reservation || null;

    updateReservationCard();
    renderLot();
  } catch (error) {
    console.error("Could not load active reservation:", error);
  }
}

// User-side arrival confirmation is intentionally removed.
// Only the admin can confirm arrival through the admin endpoint.

/* ===================== LIVE PARKING MAP ===================== */

async function renderLot() {
  const grid = document.getElementById("lotGrid");
  const summary = document.getElementById("mapSummary");

  if (!grid || !summary) return;

  try {
    const spaces = await apiRequest("/api/parking-spaces");
    lot = Array.isArray(spaces) ? spaces : [];

    // Mark the current user's own active space on the map.
    if (reservation) {
      lot = lot.map((space) => {
        if (
          String(space.spaceNumber) === String(reservation.spaceNumber)
        ) {
          return { ...space, status: "yours" };
        }

        return space;
      });
    }

    const freeCount = lot.filter(
      (space) => space.status === "available"
    ).length;

    summary.textContent =
      `Parking Lot · ${freeCount} of ${lot.length || TOTAL_SPACES} spaces free`;

    grid.innerHTML = lot
      .map((space) => {
        let cssStatus = "occupied";

        if (space.status === "available") {
          cssStatus = "free";
        } else if (space.status === "yours") {
          cssStatus = "yours";
        }

        const displayNumber = String(space.spaceNumber).padStart(2, "0");

        return `
          <div
            class="space-cell ${cssStatus}"
            onclick="clickSpace('${displayNumber}', '${space.status}', ${space.id})"
            title="Space ${displayNumber}: ${space.status}"
          >
            ${space.status === "yours" ? "" : displayNumber}
          </div>
        `;
      })
      .join("");
  } catch (error) {
    console.error("Could not load parking spaces:", error);
    summary.textContent = "Unable to load parking spaces.";
    grid.innerHTML = "";
  }
}

function clickSpace(spaceNumber, status, spaceId) {
  if (status === "yours") {
    toast(`Space ${spaceNumber} is your active reservation.`);
    return;
  }

  if (status !== "available") {
    toast(`Space ${spaceNumber} is not available.`);
    return;
  }

  if (reservation) {
    toast("You already have an active reservation request.");
    return;
  }

  const title = document.getElementById("spaceModalTitle");
  const subtitle = document.getElementById("spaceModalSub");
  const modal = document.getElementById("spaceModal");

  if (title) title.textContent = `Space ${spaceNumber}`;

  if (subtitle) {
    subtitle.textContent = "Parking Lot · Available now";
  }

  if (modal) {
    modal.dataset.space = spaceNumber;
    modal.dataset.spaceId = spaceId;
  }

  openModal("spaceModal");
}

/* ===================== SEND RESERVATION REQUEST ===================== */

async function reserveFromMap() {
  const modal = document.getElementById("spaceModal");
  const spaceId = Number(modal?.dataset.spaceId);
  const spaceNumber = modal?.dataset.space;

  if (!spaceId) {
    toast("Please select a parking space first.");
    return;
  }

  if (reservation) {
    toast("You already have an active reservation request.");
    closeModal("spaceModal");
    return;
  }

  try {
    const result = await apiRequest("/api/reservations", {
      method: "POST",
      body: JSON.stringify({ spaceId }),
    });

    toast(result.message || `Request sent for space ${spaceNumber}.`);
    closeModal("spaceModal");

    await loadActiveReservation();
    await renderLot();
  } catch (error) {
    console.error("Reservation request failed:", error);
    toast(error.message || "Could not send reservation request.");
  }
}

/* ===================== VEHICLES ===================== */

// Vehicle storage/API connection has not been added yet.
// Do not show fake vehicles for every account.

function vehicleIcon(vehicle) {
  return vehicle.type === "EV" ? "🔋" : "🚗";
}

function renderVehicles() {
  const primaryBox = document.getElementById("primaryVehicleBox");
  const otherBox = document.getElementById("otherVehiclesBox");
  const allList = document.getElementById("allVehiclesList");

  const primary = vehicles.find((vehicle) => vehicle.primary) || vehicles[0];
  const others = vehicles.filter((vehicle) => vehicle !== primary);

  if (primaryBox) {
    primaryBox.innerHTML = primary
      ? `
        <div class="vehicle-row">
          <div class="vehicle-ic">${vehicleIcon(primary)}</div>
          <div>
            <b>${primary.label}</b>
            <span>Plate ${primary.plate}</span>
          </div>
        </div>
      `
      : `<p style="color:var(--faint);font-size:13px;">No vehicle added yet.</p>`;
  }

  if (otherBox) {
    otherBox.innerHTML = others
      .map(
        (vehicle) => `
          <div class="vehicle-row">
            <div class="vehicle-ic">${vehicleIcon(vehicle)}</div>
            <div>
              <b>${vehicle.label}</b>
              <span>${vehicle.type} · ${vehicle.plate}</span>
            </div>
            <button class="rm" onclick="removeVehicle(${vehicle.id})">
              Remove
            </button>
          </div>
        `
      )
      .join("");
  }

  if (allList) {
    allList.innerHTML = vehicles.length
      ? vehicles
          .map(
            (vehicle) => `
              <div class="vehicle-row">
                <div class="vehicle-ic">${vehicleIcon(vehicle)}</div>
                <div>
                  <b>${vehicle.label}${vehicle.primary ? " (Primary)" : ""}</b>
                  <span>${vehicle.type} · Plate ${vehicle.plate}</span>
                </div>
                ${
                  vehicle.primary
                    ? ""
                    : `<button class="rm" onclick="setPrimary(${vehicle.id})">Set primary</button>`
                }
                <button class="rm" onclick="removeVehicle(${vehicle.id})">
                  Remove
                </button>
              </div>
            `
          )
          .join("")
      : `<p style="color:var(--faint);font-size:13px;">No vehicles added yet.</p>`;
  }
}

function removeVehicle(id) {
  const vehicle = vehicles.find((item) => item.id === id);
  if (!vehicle) return;

  if (!confirm(`Remove ${vehicle.label}?`)) return;

  vehicles = vehicles.filter((item) => item.id !== id);

  if (vehicle.primary && vehicles.length) {
    vehicles[0].primary = true;
  }

  renderVehicles();
  toast(`${vehicle.label} removed from this page.`);
}

function setPrimary(id) {
  vehicles.forEach((vehicle) => {
    vehicle.primary = vehicle.id === id;
  });

  renderVehicles();
  toast("Primary vehicle updated on this page.");
}

function submitVehicle() {
  const makeModel = document.getElementById("vMakeModel")?.value.trim();
  const plate = document.getElementById("vPlate")?.value.trim();
  const type = document.getElementById("vType")?.value;

  if (!makeModel || !plate) {
    toast("Enter a make/model and plate.");
    return;
  }

  vehicles.push({
    id: Date.now(),
    label: makeModel,
    plate,
    type: type || "Gas",
    primary: vehicles.length === 0,
  });

  document.getElementById("vMakeModel").value = "";
  document.getElementById("vPlate").value = "";

  closeModal("vehicleModal");
  renderVehicles();
  toast(`${makeModel} added for this page.`);
}

/* ===================== ACTIVITY / HISTORY / STATS ===================== */

// Demo history has been removed until real history is connected.

function renderActivity() {
  const list = document.getElementById("recentActivityList");
  const body = document.getElementById("historyTableBody");

  if (list) {
    list.innerHTML = activity.length
      ? activity
          .slice(0, 3)
          .map(
            (item) => `
              <div class="activity-row">
                <div class="activity-check">✓</div>
                <div>
                  <b>${item.place}</b>
                  <span>${item.date} · ${item.duration} · ${item.spot}</span>
                </div>
                <div class="activity-price">$${item.price.toFixed(2)}</div>
              </div>
            `
          )
          .join("")
      : `<p style="color:var(--faint);font-size:13px;">No parking activity yet.</p>`;
  }

  if (body) {
    body.innerHTML = activity
      .map(
        (item) => `
          <tr>
            <td>${item.place}</td>
            <td>${item.date}</td>
            <td>${item.duration}</td>
            <td>${item.spot}</td>
            <td>$${item.price.toFixed(2)}</td>
          </tr>
        `
      )
      .join("");
  }
}

function renderStats() {
  const sessions = activity.length;
  const hours = activity.reduce((sum, item) => sum + item.hours, 0);
  const spent = activity.reduce((sum, item) => sum + item.price, 0);
  const average = sessions ? spent / sessions : 0;

  const values = {
    statSessions: sessions,
    statHours: hours.toFixed(1),
    statSpent: "$" + spent.toFixed(2),
    statAvg: "$" + average.toFixed(2),
  };

  Object.entries(values).forEach(([id, value]) => {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  });
}

/* ===================== SETTINGS ===================== */

function saveSettings() {
  const name = document.getElementById("setName")?.value.trim();

  if (name) {
    const nameElement = document.querySelector(".user-chip .name");
    if (nameElement) nameElement.textContent = name;

    const greeting = document.getElementById("greeting");
    if (greeting) {
      greeting.textContent = greeting.textContent.replace(
        /,\s*.+$/,
        ", " + name.split(" ")[0]
      );
    }
  }

  toast("Settings updated on this page.");
}

/* ===================== SUPPORT ===================== */

function submitSupport() {
  const input = document.getElementById("supportMsg");
  const message = input?.value.trim();

  if (!message) {
    toast("Type a message first.");
    return;
  }

  input.value = "";
  closeModal("supportModal");
  toast("Support form is not connected to the backend yet.");
}

/* INITIALIZE */

async function initializeDashboard() {
  // Remove the regular user's arrival confirmation button.
  const arrivalButton = document.getElementById("confirmArrivalBtn");

  if (arrivalButton) {
    arrivalButton.style.display = "none";
  }

  renderVehicles();
  renderActivity();
  renderStats();
  renderBell();

  await loadActiveReservation();
  await renderLot();
}

initializeDashboard();