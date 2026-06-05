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

/* ---- Sound: synthesized chimes via Web Audio (no audio files needed) ---- */
const Sound = {
  ctx: null,
  get enabled() { return localStorage.getItem("soundEnabled") !== "0"; },
  set enabled(v) { localStorage.setItem("soundEnabled", v ? "1" : "0"); },
  _ensure() {
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) this.ctx = new AC();
    }
    // Browsers suspend audio until a user gesture; resume opportunistically.
    if (this.ctx && this.ctx.state === "suspended") this.ctx.resume();
    return this.ctx;
  },
  _tone(freq, start, dur, type = "sine", peak = 0.18) {
    const ctx = this.ctx;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    const t0 = ctx.currentTime + start;
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.exponentialRampToValueAtTime(peak, t0 + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(gain).connect(ctx.destination);
    osc.start(t0);
    osc.stop(t0 + dur + 0.02);
  },
  play(kind) {
    if (!this.enabled) return;
    const ctx = this._ensure();
    if (!ctx) return;
    try {
      if (kind === "notification") {
        // Pleasant rising two-tone chime.
        this._tone(880, 0, 0.18, "sine", 0.2);
        this._tone(1318.5, 0.12, 0.22, "sine", 0.2);
      } else if (kind === "alert") {
        // Lower, attention-grabbing double buzz.
        this._tone(440, 0, 0.16, "square", 0.12);
        this._tone(330, 0.18, 0.22, "square", 0.12);
      } else {
        // Subtle confirmation blip.
        this._tone(660, 0, 0.12, "triangle", 0.14);
      }
    } catch (e) { /* ignore audio errors */ }
  },
};

function toast(msg, type = "success") {
  const el = document.createElement("div");
  el.className = `alert alert-${type} position-fixed shadow`;
  el.style.cssText = "top:1rem;right:1rem;z-index:2000;min-width:260px";
  el.textContent = msg;
  document.body.appendChild(el);
  // Audible feedback: errors/warnings -> alert buzz, success -> confirm blip.
  // "info" stays silent because realtime notifications play their own chime.
  if (type === "danger" || type === "warning") Sound.play("alert");
  else if (type === "success") Sound.play("success");
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

function refreshSoundToggle() {
  const btn = document.getElementById("soundToggle");
  if (!btn) return;
  const on = Sound.enabled;
  btn.innerHTML = `<i class="bi bi-volume-${on ? "up" : "mute"}"></i>`;
  btn.title = on ? "Mute sounds" : "Unmute sounds";
}

/* Initialise Bootstrap tooltips on every element that has a title (or an
   explicit data-bs-toggle="tooltip"). Safe to call repeatedly — already
   initialised elements are skipped, so it also covers dynamically added DOM. */
function initTooltips(root = document) {
  if (!window.bootstrap || !bootstrap.Tooltip) return;
  const sel = '[title]:not([data-tt]), [data-bs-toggle="tooltip"]:not([data-tt])';
  root.querySelectorAll(sel).forEach((el) => {
    const text = el.getAttribute("title") || el.getAttribute("data-bs-title");
    if (!text) return;
    el.setAttribute("data-tt", "1");
    new bootstrap.Tooltip(el, { trigger: "hover focus", container: "body" });
  });
}
window.initTooltips = initTooltips;

document.addEventListener("DOMContentLoaded", () => {
  wireDeletes();
  refreshSoundToggle();
  initTooltips();

  // Unlock the audio context on the first user gesture (autoplay policy).
  const unlock = () => { Sound._ensure(); window.removeEventListener("click", unlock); window.removeEventListener("keydown", unlock); };
  window.addEventListener("click", unlock);
  window.addEventListener("keydown", unlock);

  // Sound mute toggle
  const soundBtn = document.getElementById("soundToggle");
  if (soundBtn) {
    soundBtn.addEventListener("click", () => {
      Sound.enabled = !Sound.enabled;
      refreshSoundToggle();
      if (Sound.enabled) Sound.play("notification");  // preview when enabling
      toast(Sound.enabled ? "Sounds on" : "Sounds muted", "info");
    });
  }

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
