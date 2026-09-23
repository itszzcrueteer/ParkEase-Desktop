(function () {
  const form = document.getElementById("signupForm");
  const submitBtn = document.getElementById("submitBtn");
  const banner = document.getElementById("statusBanner");

  const fields = {
    firstName: document.getElementById("firstName"),
    lastName: document.getElementById("lastName"),
    email: document.getElementById("email"),
    vehicle: document.getElementById("vehicle"),
    plate: document.getElementById("plate"),
    password: document.getElementById("password"),
    confirmPassword: document.getElementById("confirmPassword"),
    terms: document.getElementById("terms"),
  };

  // Show/hide password toggles
  document.querySelectorAll(".toggle-visibility").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = document.getElementById(btn.dataset.toggleFor);
      const isHidden = input.type === "password";
      input.type = isHidden ? "text" : "password";
      btn.textContent = isHidden ? "Hide" : "Show";
    });
  });

  function setError(field, message) {
    const el = document.querySelector(`[data-error-for="${field}"]`);
    if (el) el.textContent = message || "";
    if (fields[field] && fields[field].type !== "checkbox") {
      fields[field].classList.toggle("invalid", Boolean(message));
    }
  }

  function clearErrors() {
    Object.keys(fields).forEach((key) => setError(key, ""));
  }

  function showBanner(message, type) {
    banner.textContent = message;
    banner.className = `status-banner show ${type}`;
  }

  function validate() {
    clearErrors();
    let valid = true;

    if (!fields.firstName.value.trim()) {
      setError("firstName", "First name is required.");
      valid = false;
    }
    if (!fields.lastName.value.trim()) {
      setError("lastName", "Last name is required.");
      valid = false;
    }

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(fields.email.value.trim())) {
      setError("email", "Enter a valid email address.");
      valid = false;
    }

    if (!fields.vehicle.value.trim()) {
      setError("vehicle", "Vehicle make/model is required.");
      valid = false;
    }
    if (!fields.plate.value.trim()) {
      setError("plate", "License plate is required.");
      valid = false;
    }

    if (fields.password.value.length < 8) {
      setError("password", "Password must be at least 8 characters.");
      valid = false;
    }
    if (fields.confirmPassword.value !== fields.password.value) {
      setError("confirmPassword", "Passwords do not match.");
      valid = false;
    }

    if (!fields.terms.checked) {
      setError("terms", "You must agree to the Terms and Privacy Policy.");
      valid = false;
    }

    return valid;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    banner.className = "status-banner";

    if (!validate()) return;

    const payload = {
      firstName: fields.firstName.value.trim(),
      lastName: fields.lastName.value.trim(),
      email: fields.email.value.trim(),
      vehicle: fields.vehicle.value.trim(),
      licensePlate: fields.plate.value.trim(),
      password: fields.password.value,
    };

    submitBtn.disabled = true;
    submitBtn.textContent = "Creating account…";

    try {
      const { apiBaseUrl, endpoints } = window.PARKEASE_CONFIG;
      const res = await fetch(apiBaseUrl + endpoints.signup, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.message || "Could not create account.");
      }

      showBanner("Account created. Redirecting to login…", "success");
      setTimeout(() => {
        window.location.href = "login.html";
      }, 1200);
    } catch (err) {
      showBanner(err.message || "Something went wrong. Please try again.", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Create Account";
    }
  });
})();
