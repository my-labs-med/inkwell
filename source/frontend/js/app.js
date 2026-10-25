import { api as loadApi } from "./api.js";
import { handleCallback, profile, signIn, signOut, token } from "./auth.js";
import { applyCompletion, calendarGrid, currentStreak, inkLevel, localDay } from "./stats.js";

const STATS_REFRESH_MS = 65000;
const UNDO_MS = 5000;

const $ = (id) => document.getElementById(id);
const state = {
  tasks: [],
  stats: { totalDone: 0, longestStreak: 0, milestones: [], days: {} },
  filter: "all",
  statsFetchedAt: 0,
  editing: null,
};
const rows = new Map();
const pending = new Map();
const pendingDeletes = new Map();
let api;

const storage = {
  get(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {}
  },
};

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const icon = $("theme").querySelector("use");
  icon.setAttribute("href", `/assets/icons.svg#${theme === "dark" ? "sun" : "moon"}`);
}

function initialTheme() {
  const saved = storage.get("inkwell.theme");
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function toast(nodes, kind = "", duration = 5000) {
  const node = document.createElement("div");
  node.className = `toast ${kind}`;
  node.append(...nodes);
  $("toasts").append(node);
  setTimeout(() => node.remove(), duration);
  return node;
}

function toastText(text, kind) {
  toast([document.createTextNode(text)], kind);
}

function greet() {
  const hour = new Date().getHours();
  const part = hour < 5 ? "Late night" : hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const name = (profile()?.email || "").split("@")[0];
  $("greeting").textContent = name ? `${part}, ${name}.` : `${part}.`;
  $("today").textContent = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

function renderStats(freshDay) {
  const today = localDay();
  const { days, totalDone, longestStreak } = state.stats;
  const streak = currentStreak(days, today);
  $("streak").textContent = streak;
  $("streak").closest(".streak").classList.toggle("lit", (days[today] || 0) > 0);
  $("total-done").textContent = totalDone;
  $("longest").textContent = Math.max(longestStreak, streak);

  const calendar = $("calendar");
  calendar.replaceChildren(
    ...calendarGrid(today).map(({ day, future }) => {
      const dot = document.createElement("span");
      const count = days[day] || 0;
      dot.className = "dot";
      dot.dataset.level = inkLevel(count);
      dot.classList.toggle("future", future);
      dot.classList.toggle("today", day === today);
      dot.classList.toggle("fresh", day === freshDay);
      if (!future) dot.title = `${day}: ${count} done`;
      return dot;
    }),
  );
}

function announceMilestones() {
  const key = `inkwell.seen.${profile()?.sub || "me"}`;
  const stored = storage.get(key);
  const current = state.stats.milestones;
  storage.set(key, JSON.stringify(current.map((m) => m.id)));
  if (stored === null) return;
  let seen;
  try {
    seen = new Set(JSON.parse(stored));
  } catch {
    seen = new Set();
  }
  for (const milestone of current.filter((m) => !seen.has(m.id))) {
    const title = document.createElement("strong");
    title.textContent = milestone.title;
    const text = document.createElement("span");
    text.append(title, " — a note is waiting in your inbox.");
    toast([text]);
  }
}

async function loadStats() {
  try {
    state.stats = await api.getStats();
    state.statsFetchedAt = Date.now();
    renderStats();
    announceMilestones();
  } catch (error) {
    if (error.status !== 401) toastText("Couldn't load your stats.", "error");
  }
}

function visibleTasks() {
  if (state.filter === "all") return state.tasks;
  return state.tasks.filter((task) => task.status === state.filter);
}

function fillRow(row, task) {
  const done = task.status === "done";
  row.classList.toggle("done", done);
  row.querySelector(".check").setAttribute("aria-label", done ? `Reopen “${task.title}”` : `Finish “${task.title}”`);
  row.querySelector(".check").setAttribute("aria-pressed", String(done));
  row.querySelector(".task-title").textContent = task.title;
  row.querySelector(".task-notes").textContent = task.description || "";
  const chip = row.querySelector(".chip");
  chip.dataset.status = task.status;
  chip.textContent = task.status === "doing" ? "doing" : "to do";
  chip.setAttribute("aria-label", task.status === "doing" ? "Move back to to do" : "Start doing");
  row.querySelector(".delete").setAttribute("aria-label", `Delete “${task.title}”`);
}

function createRow(task) {
  const row = $("task-template").content.firstElementChild.cloneNode(true);
  row.dataset.id = task.taskId;
  return row;
}

function renderTasks() {
  const list = $("tasks");
  const visible = visibleTasks();
  const ids = new Set(visible.map((task) => task.taskId));

  for (const [id, row] of rows) {
    if (!ids.has(id)) {
      row.remove();
      rows.delete(id);
    }
  }
  visible.forEach((task, index) => {
    let row = rows.get(task.taskId);
    if (!row) {
      row = createRow(task);
      rows.set(task.taskId, row);
    }
    if (state.editing !== task.taskId) fillRow(row, task);
    if (list.children[index] !== row) list.insertBefore(row, list.children[index] || null);
  });

  $("empty").hidden = visible.length > 0;
  $("empty").textContent =
    state.filter === "all" ? "A blank page. Write the first line." : "Nothing here yet.";

  for (const tab of document.querySelectorAll(".tabs button")) {
    const filter = tab.dataset.filter;
    const count = filter === "all" ? state.tasks.length : state.tasks.filter((t) => t.status === filter).length;
    tab.querySelector("span").textContent = count || "";
    tab.setAttribute("aria-selected", String(filter === state.filter));
  }
}

function findTask(id) {
  return state.tasks.find((task) => task.taskId === id);
}

function replaceTask(id, next) {
  state.tasks = state.tasks.map((task) => (task.taskId === id ? next : task));
  if (next.taskId !== id) {
    const row = rows.get(id);
    rows.delete(id);
    if (row) {
      row.dataset.id = next.taskId;
      rows.set(next.taskId, row);
    }
  }
}

function enqueue(id, job) {
  const previous = pending.get(id) || Promise.resolve();
  const next = previous.then(job, job);
  pending.set(id, next);
  next.finally(() => {
    if (pending.get(id) === next) pending.delete(id);
  });
  return next;
}

function isLatest(id, job) {
  return pending.get(id) === job;
}

async function resync(error) {
  if (error.status === 401) return;
  toastText(error.message, "error");
  try {
    state.tasks = await api.listTasks();
    renderTasks();
  } catch {}
  await loadStats();
}

function update(task, fields) {
  const optimistic = { ...task, ...fields };
  let freshDay;

  if (fields.status === "done" && task.status !== "done") {
    optimistic.completedDay = localDay();
    state.stats = applyCompletion(state.stats, optimistic.completedDay, 1);
    freshDay = optimistic.completedDay;
  } else if (fields.status && fields.status !== "done" && task.status === "done") {
    state.stats = applyCompletion(state.stats, task.completedDay || localDay(), -1);
    delete optimistic.completedDay;
  }

  replaceTask(task.taskId, optimistic);
  renderTasks();
  if (fields.status) renderStats(freshDay);

  const job = enqueue(task.taskId, async () => {
    try {
      const saved = await api.updateTask(task.taskId, fields);
      if (isLatest(task.taskId, job)) {
        replaceTask(task.taskId, saved);
        renderTasks();
      }
    } catch (error) {
      await resync(error);
    }
  });
}

async function create(title) {
  const now = new Date().toISOString();
  const draft = { taskId: `draft-${Date.now()}`, title, description: "", status: "todo", createdAt: now };
  state.tasks = [draft, ...state.tasks];
  renderTasks();
  try {
    replaceTask(draft.taskId, await api.createTask({ title }));
    renderTasks();
  } catch (error) {
    state.tasks = state.tasks.filter((task) => task !== draft);
    renderTasks();
    $("new-title").value ||= title;
    if (error.status !== 401) toastText(error.message, "error");
  }
}

function commitDelete(id) {
  const entry = pendingDeletes.get(id);
  if (!entry) return;
  pendingDeletes.delete(id);
  clearTimeout(entry.timer);
  entry.toast.remove();
  enqueue(id, async () => {
    try {
      await api.deleteTask(id);
    } catch (error) {
      await resync(error);
    }
  });
}

function undoDelete(id) {
  const entry = pendingDeletes.get(id);
  if (!entry) return;
  pendingDeletes.delete(id);
  clearTimeout(entry.timer);
  entry.toast.remove();
  state.tasks.splice(Math.min(entry.index, state.tasks.length), 0, entry.task);
  renderTasks();
}

async function remove(task) {
  const id = task.taskId;
  rows.get(id)?.classList.add("leaving");
  await new Promise((resolve) => setTimeout(resolve, 220));
  const index = state.tasks.findIndex((t) => t.taskId === id);
  state.tasks = state.tasks.filter((t) => t.taskId !== id);
  rows.get(id)?.classList.remove("leaving");
  renderTasks();

  const label = document.createElement("span");
  label.textContent = `Deleted “${task.title}”`;
  const undo = document.createElement("button");
  undo.type = "button";
  undo.className = "toast-action";
  undo.textContent = "Undo";
  undo.addEventListener("click", () => undoDelete(id));
  pendingDeletes.set(id, {
    task,
    index,
    toast: toast([label, undo], "", UNDO_MS + 1000),
    timer: setTimeout(() => commitDelete(id), UNDO_MS),
  });
}

function startEdit(row, task) {
  state.editing = task.taskId;
  const form = row.querySelector(".task-edit");
  row.querySelector(".task-title").hidden = true;
  row.querySelector(".task-notes").hidden = true;
  form.hidden = false;
  form.querySelector(".edit-title").value = task.title;
  form.querySelector(".edit-notes").value = task.description || "";
  form.querySelector(".edit-title").focus();
}

function stopEdit(row) {
  state.editing = null;
  row.querySelector(".task-edit").hidden = true;
  row.querySelector(".task-title").hidden = false;
  row.querySelector(".task-notes").hidden = false;
  const task = findTask(row.dataset.id);
  if (task) fillRow(row, task);
}

function bindEvents() {
  $("theme").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    storage.set("inkwell.theme", next);
    applyTheme(next);
  });
  $("sign-out").addEventListener("click", signOut);

  $("compose").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = $("new-title");
    const title = input.value.trim();
    if (!title) return;
    input.value = "";
    create(title);
  });

  document.querySelector(".tabs").addEventListener("click", (event) => {
    const tab = event.target.closest("button[data-filter]");
    if (!tab) return;
    state.filter = tab.dataset.filter;
    renderTasks();
  });

  const list = $("tasks");
  list.addEventListener("click", (event) => {
    const row = event.target.closest(".task");
    const task = row && findTask(row.dataset.id);
    if (!task || task.taskId.startsWith("draft-")) return;
    if (event.target.closest(".check")) {
      update(task, { status: task.status === "done" ? "todo" : "done" });
    } else if (event.target.closest(".chip")) {
      update(task, { status: task.status === "doing" ? "todo" : "doing" });
    } else if (event.target.closest(".task-title")) {
      startEdit(row, task);
    } else if (event.target.closest(".delete")) {
      remove(task);
    } else if (event.target.closest(".cancel")) {
      stopEdit(row);
    }
  });

  list.addEventListener("submit", (event) => {
    event.preventDefault();
    const row = event.target.closest(".task");
    const task = findTask(row.dataset.id);
    const title = row.querySelector(".edit-title").value.trim();
    const description = row.querySelector(".edit-notes").value.trim();
    stopEdit(row);
    if (task && title && (title !== task.title || description !== (task.description || ""))) {
      update(task, { title, description });
    }
  });

  list.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && event.target.closest(".task-edit")) {
      stopEdit(event.target.closest(".task"));
    }
  });

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      for (const id of [...pendingDeletes.keys()]) commitDelete(id);
    }
    if (document.visibilityState === "visible" && Date.now() - state.statsFetchedAt > STATS_REFRESH_MS) {
      loadStats();
    }
  });
}

async function init() {
  applyTheme(initialTheme());
  $("sign-in").addEventListener("click", signIn);
  try {
    await handleCallback();
  } catch {
    toastText("Sign-in didn't complete. Please try again.", "error");
  }

  if (!token()) {
    $("loading").hidden = true;
    $("welcome").hidden = false;
    return;
  }

  api = await loadApi();
  greet();
  bindEvents();
  renderStats();
  try {
    state.tasks = await api.listTasks();
  } catch (error) {
    if (error.status !== 401) toastText("Couldn't open your journal.", "error");
  }
  $("loading").hidden = true;
  $("journal").hidden = false;
  renderTasks();
  loadStats();
}

init();
