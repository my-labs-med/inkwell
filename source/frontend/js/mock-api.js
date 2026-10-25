import { applyCompletion, localDay } from "./stats.js";

const KEY = "inkwell.mock";

function load() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || seed();
  } catch {
    return seed();
  }
}

function save(state) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {}
}

function seed() {
  const days = {};
  const today = new Date();
  for (let i = 1; i < 84; i += 1) {
    if (Math.random() < 0.45) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      days[localDay(d)] = 1 + Math.floor(Math.random() * 5);
    }
  }
  const stamp = (n) => new Date(Date.now() - n * 60000).toISOString();
  const task = (id, title, status, minutes, description = "") => ({
    taskId: id, title, description, status, createdAt: stamp(minutes), updatedAt: stamp(minutes),
    ...(status === "done" ? { completedAt: stamp(minutes), completedDay: localDay() } : {}),
  });
  return {
    tasks: [
      task("m4", "Sketch the architecture diagram", "doing", 5, "API Gateway, Lambda, DynamoDB, Streams."),
      task("m3", "Verify the SES sender address", "todo", 30),
      task("m2", "Record the demo video", "todo", 60),
      task("m1", "Write the README", "done", 120),
    ],
    stats: {
      totalDone: Object.values(days).reduce((a, b) => a + b, 0) + 1,
      longestStreak: 9,
      milestones: [
        { id: "done:1", title: "Your first ink mark" },
        { id: "done:10", title: "10 tasks, inked" },
      ],
      days: { ...days, [localDay()]: 1 },
    },
  };
}

const delay = (value) => new Promise((resolve) => setTimeout(() => resolve(structuredClone(value)), 150));

export const mockApi = {
  async listTasks() {
    return delay(load().tasks);
  },
  async createTask(fields) {
    const state = load();
    const now = new Date().toISOString();
    const task = { taskId: `m${Date.now()}`, description: "", status: "todo", ...fields, createdAt: now, updatedAt: now };
    state.tasks.unshift(task);
    save(state);
    return delay(task);
  },
  async updateTask(id, fields) {
    const state = load();
    const task = state.tasks.find((t) => t.taskId === id);
    const wasDone = task.status === "done";
    Object.assign(task, fields, { updatedAt: new Date().toISOString() });
    if (!wasDone && task.status === "done") {
      task.completedDay = localDay();
      state.stats = applyCompletion(state.stats, task.completedDay, 1);
    } else if (wasDone && task.status !== "done") {
      state.stats = applyCompletion(state.stats, task.completedDay, -1);
      delete task.completedDay;
    }
    save(state);
    return delay(task);
  },
  async deleteTask(id) {
    const state = load();
    state.tasks = state.tasks.filter((t) => t.taskId !== id);
    save(state);
    return delay(null);
  },
  async getStats() {
    return delay(load().stats);
  },
};
