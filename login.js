(function () {
  const form = document.getElementById("loginForm");
  const submitBtn = document.getElementById("submitBtn");
  const banner = document.getElementById("statusBanner");

  const fields = {
    email: document.getElementById("email"),
    password: document.getElementById("password"),
  };

  document.querySelectorAll(".toggle-visibility").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = document.getElementById(btn.dataset.toggleFor);
      const isHidden = input.type === "password";
      input.type = isHidden ? "text" : "password";
      btn.textContent = isHidden ? "🙈" : "👁";
    });
  });

  function setError(field, message) {
    const el = document.querySelector(`[data-error-for="${field}"]`);
    if (el) el.textContent = message || "";
    fields[field].classList.toggle("invalid", Boolean(message));
  }

  function showBanner(message, type) {
    banner.textContent = message;
    banner.className = `status-banner show ${type}`;
  }

  function validate() {
    setError("email", "");
    setError("password", "");
    let valid = true;

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(fields.email.value.trim())) {
      setError("email", "Enter a valid email address.");
      valid = false;
    }
    if (!fields.password.value) {
      setError("password", "Password is required.");
      valid = false;
    }
    return valid;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    banner.className = "status-banner";

    if (!validate()) return;

    const payload = {
      email: fields.email.value.trim(),
      password: fields.password.value,
      keepLoggedIn: document.getElementById("keepLoggedIn").checked,
    };

    submitBtn.disabled = true;
    submitBtn.textContent = "Logging in…";

    try {
      const { apiBaseUrl, endpoints } = window.PARKEASE_CONFIG;
      const res = await fetch(apiBaseUrl + endpoints.login, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.message || "Invalid email or password.");
      }

      const data = await res.json().catch(() => ({}));
      if (data.token) {
        const storage = payload.keepLoggedIn ? window.localStorage : window.sessionStorage;
        storage.setItem("parkease_token", data.token);
      }

      showBanner("Logged in. Redirecting…", "success");
      setTimeout(() => {
        // Regular users land on their dashboard; route admins to dashboard.html instead
        // once the backend returns a role/permissions flag on data.
        window.location.href = "user-dashboard.html";
      }, 900);
    } catch (err) {
      showBanner(err.message || "Something went wrong. Please try again.", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Log in";
    }
  });

  // OAuth stubs — wire these up to your real OAuth flow when the backend is ready.
  document.getElementById("googleLogin").addEventListener("click", () => {
    showBanner("Google login not wired up yet.", "error");
  });
  document.getElementById("appleLogin").addEventListener("click", () => {
    showBanner("Apple login not wired up yet.", "error");
  });
})();
