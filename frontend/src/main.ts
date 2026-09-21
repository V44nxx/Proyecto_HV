import "./styles/variables.css";
import "./styles/base.css";
import "./styles/components.css";

import { Router } from "./router";
import { authStore } from "./store/authStore";

document.addEventListener("DOMContentLoaded", () => {
  const appContainer = document.getElementById("app");
  if (!appContainer) {
    console.error("Root element #app not found");
    return;
  }

  const router = new Router(appContainer);
  router.init();

  // Re-route on auth state changes
  authStore.subscribe(() => {
    // If not authenticated and not on login, go to login
    if (!authStore.isAuthenticated() && window.location.hash !== "#/login") {
      window.location.hash = "#/login";
    }
  });
});
