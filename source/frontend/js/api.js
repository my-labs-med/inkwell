import config from "./config.js";
import { signIn, token } from "./auth.js";
import { localDay } from "./stats.js";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(method, path, body, options = {}) {
  const current = token();
  if (!current) {
    await signIn();
    throw new ApiError("Signing you in…", 401);
  }
  const response = await fetch(`${config.apiBase}${path}`, {
    method,
    headers: {
      Authorization: current,
      "Content-Type": "application/json",
      "X-Client-Date": localDay(),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    ...options,
  });
  if (response.status === 401) {
    await signIn();
    throw new ApiError("Signing you in…", 401);
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(data?.error?.message || "Something went wrong", response.status);
  }
  return data;
}

const remote = {
  listTasks: () => request("GET", "/tasks").then((data) => data.tasks),
  createTask: (fields) => request("POST", "/tasks", fields),
  updateTask: (id, fields) => request("PUT", `/tasks/${encodeURIComponent(id)}`, fields),
  deleteTask: (id) => request("DELETE", `/tasks/${encodeURIComponent(id)}`, undefined, { keepalive: true }),
  getStats: () => request("GET", "/stats", undefined, { cache: "no-cache" }),
};

export async function api() {
  if (!config.mock) return remote;
  const { mockApi } = await import("./mock-api.js");
  return mockApi;
}
