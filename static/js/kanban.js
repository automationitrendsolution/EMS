/* Trello-like Kanban board with drag & drop + realtime sync (Module 5). */
(function () {
  const board = document.getElementById("kanban");
  if (!board) return;
  const projectId = board.dataset.projectId;
  let filters = { search: "", assigned_to_id: "" };

  function priorityClass(p) { return "p-" + p; }

  function cardHtml(t) {
    const due = t.due_date ? new Date(t.due_date).toLocaleDateString() : "";
    const overdue = t.is_overdue ? '<span class="badge bg-danger ms-1">Overdue</span>' : "";
    const assignee = t.assigned_to ? t.assigned_to.full_name : "Unassigned";
    return `<div class="kanban-card" draggable="true" data-id="${t.id}">
      <div class="d-flex justify-content-between align-items-start">
        <span class="card-title">${escapeHtml(t.title)}</span>
        <span class="priority-dot ${priorityClass(t.priority)}" title="${t.priority}"></span>
      </div>
      <div class="meta mt-1">${t.task_id} · ${escapeHtml(assignee)}</div>
      <div class="progress progress-thin my-2"><div class="progress-bar" style="width:${t.progress}%"></div></div>
      <div class="meta d-flex justify-content-between">
        <span><i class="bi bi-list-check"></i> ${t.subtask_count}</span>
        <span>${due} ${overdue}</span>
      </div>
      <a href="/tasks/${t.id}/" class="stretched-link" style="display:none"></a>
    </div>`;
  }

  function escapeHtml(s) {
    return (s || "").replace(/[&<>"]/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  async function load() {
    const q = new URLSearchParams();
    if (filters.search) q.set("search", filters.search);
    if (filters.assigned_to_id) q.set("assigned_to_id", filters.assigned_to_id);
    const data = await API.get(`/kanban/${projectId}/?` + q.toString());
    board.innerHTML = "";
    data.columns.forEach((col) => {
      const el = document.createElement("div");
      el.className = "kanban-col";
      el.dataset.status = col.key;
      el.innerHTML = `<h6>${col.label} <span class="badge bg-secondary">${col.tasks.length}</span></h6>
        <div class="col-body"></div>`;
      const body = el.querySelector(".col-body");
      col.tasks.forEach((t) => body.insertAdjacentHTML("beforeend", cardHtml(t)));
      board.appendChild(el);
    });
    wireDnd();
  }

  function wireDnd() {
    let dragged = null;
    board.querySelectorAll(".kanban-card").forEach((card) => {
      card.addEventListener("dragstart", () => { dragged = card; card.classList.add("dragging"); });
      card.addEventListener("dragend", () => { card.classList.remove("dragging"); });
      card.addEventListener("dblclick", () => { location.href = `/tasks/${card.dataset.id}/`; });
    });
    board.querySelectorAll(".kanban-col").forEach((col) => {
      const body = col.querySelector(".col-body");
      col.addEventListener("dragover", (e) => { e.preventDefault(); col.classList.add("drag-over"); });
      col.addEventListener("dragleave", () => col.classList.remove("drag-over"));
      col.addEventListener("drop", async (e) => {
        e.preventDefault();
        col.classList.remove("drag-over");
        if (!dragged) return;
        body.appendChild(dragged);
        const order = [...body.children].indexOf(dragged);
        try {
          await API.post(`/tasks/${dragged.dataset.id}/move/`, {
            status: col.dataset.status, board_order: order,
          });
        } catch (err) { toast(err.message, "danger"); load(); }
      });
    });
  }

  // Realtime updates
  function connectWs() {
    const ws = new WebSocket(wsUrl(`/ws/kanban/${projectId}/`));
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      // Reload on any board change not initiated locally (simple + robust).
      load();
    };
    ws.onclose = () => setTimeout(connectWs, 4000);
  }

  // Filters
  const searchInput = document.getElementById("boardSearch");
  if (searchInput) searchInput.addEventListener("input", (e) => {
    filters.search = e.target.value; load();
  });
  const assigneeSel = document.getElementById("boardAssignee");
  if (assigneeSel) assigneeSel.addEventListener("change", (e) => {
    filters.assigned_to_id = e.target.value; load();
  });

  load();
  connectWs();
})();
