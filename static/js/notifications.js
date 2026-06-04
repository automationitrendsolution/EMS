/* Realtime notification badge via WebSocket (Module 11). */
(function () {
  if (!window.API_TOKEN) return;
  let ws;
  function connect() {
    ws = new WebSocket(wsUrl("/ws/notifications/"));
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      const badge = document.querySelector(".notif-badge");
      if (badge) {
        badge.style.display = "inline-block";
        badge.textContent = (parseInt(badge.textContent || "0", 10) || 0) + 1;
      }
      toast(`🔔 ${data.title}`, "info");
    };
    ws.onclose = () => setTimeout(connect, 4000);
  }
  connect();
})();
