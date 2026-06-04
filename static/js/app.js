/* Shared frontend helpers: REST client (JWT) + theme + sidebar. */
const API = {
  base: "/api/v1",
  async request(method, path, body, isForm = false) {
    const headers = { Authorization: "Bearer " + window.API_TOKEN };
    let payload = body;
    if (body && !isForm) {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    }
    const res = await fetch(this.base + path, { method, headers, body: payload });
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Request failed");
    return data;
  },
  get(p) { return this.request("GET", p); },
  post(p, b) { return this.request("POST", p, b); },
  patch(p, b) { return this.request("PATCH", p, b); },
  del(p) { return this.request("DELETE", p); },
  postForm(p, formData) { return this.request("POST", p, formData, true); },
};

function toast(msg, type = "success") {
  const el = document.createElement("div");
  el.className = `alert alert-${type} position-fixed shadow`;
  el.style.cssText = "top:1rem;right:1rem;z-index:2000;min-width:260px";
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

function wsUrl(path) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}${path}?token=${window.API_TOKEN}`;
}

/* Generic delete handler.
   Add to any button: data-delete-url="/api/v1/..." plus one of:
     data-redirect="/path/"   navigate here on success
     data-remove="#selector"  remove this DOM node on success
   Optional: data-confirm="message" overrides the confirm text. */
async function wireDeletes(root = document) {
  root.querySelectorAll("[data-delete-url]").forEach((el) => {
    if (el.dataset.deleteBound) return;
    el.dataset.deleteBound = "1";
    el.addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const msg = el.dataset.confirm || "Delete this item? This cannot be undone.";
      if (!confirm(msg)) return;
      // Accept either a full "/api/v1/..." URL or a path relative to API.base.
      let path = el.dataset.deleteUrl;
      if (path.startsWith(API.base + "/")) path = path.slice(API.base.length);
      try {
        await API.del(path);
        toast("Deleted");
        if (el.dataset.redirect) {
          location.href = el.dataset.redirect;
        } else if (el.dataset.remove) {
          document.querySelector(el.dataset.remove)?.remove();
        } else {
          location.reload();
        }
      } catch (err) {
        toast(err.message, "danger");
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  wireDeletes();
  // Theme toggle
  const themeBtn = document.getElementById("themeToggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const html = document.documentElement;
      const next = html.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      html.setAttribute("data-bs-theme", next);
      document.cookie = `theme=${next};path=/;max-age=31536000`;
    });
  }
  // Sidebar toggle (mobile)
  const sbBtn = document.getElementById("sidebarToggle");
  if (sbBtn) {
    sbBtn.addEventListener("click", () => {
      document.getElementById("sidebar").classList.toggle("show");
    });
  }
});
