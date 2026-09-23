// Central place to point the frontend at your backend.
// Swap this out once the team decides the real API host (Flask/Django/Node/etc).
window.PARKEASE_CONFIG = {
  apiBaseUrl: "http://localhost:5000/api", // e.g. Flask dev server
  endpoints: {
    signup: "/auth/signup",
    login: "/auth/login",
  },
};
