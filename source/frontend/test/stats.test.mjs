import assert from "node:assert/strict";
import { test } from "node:test";

import { applyCompletion, calendarGrid, currentStreak, inkLevel, localDay } from "../js/stats.js";

test("current streak counts back from today", () => {
  const days = { "2026-10-23": 1, "2026-10-24": 2, "2026-10-25": 1 };
  assert.equal(currentStreak(days, "2026-10-25"), 3);
});

test("current streak survives until today is done", () => {
  assert.equal(currentStreak({ "2026-10-23": 1, "2026-10-24": 1 }, "2026-10-25"), 2);
});

test("a gap breaks the streak", () => {
  assert.equal(currentStreak({ "2026-10-22": 4 }, "2026-10-25"), 0);
  assert.equal(currentStreak({}, "2026-10-25"), 0);
});

test("streak crosses month and year boundaries", () => {
  assert.equal(currentStreak({ "2025-12-31": 1, "2026-01-01": 1 }, "2026-01-01"), 2);
});

test("calendar has 84 cells ending in the current week, starting on a Monday", () => {
  const cells = calendarGrid("2026-10-25");
  assert.equal(cells.length, 84);
  assert.equal(new Date(`${cells[0].day}T00:00:00Z`).getUTCDay(), 1);
  const past = cells.filter((c) => !c.future);
  assert.equal(past.at(-1).day, "2026-10-25");
  assert.equal(cells.at(-1).day, "2026-10-25");
});

test("calendar marks the rest of the week as future", () => {
  const cells = calendarGrid("2026-10-21");
  assert.deepEqual(
    cells.filter((c) => c.future).map((c) => c.day),
    ["2026-10-22", "2026-10-23", "2026-10-24", "2026-10-25"],
  );
});

test("ink levels", () => {
  assert.deepEqual([0, 1, 2, 3, 4, 5, 6, 20].map(inkLevel), [0, 1, 2, 2, 3, 3, 4, 4]);
});

test("applyCompletion adds and removes days", () => {
  const start = { totalDone: 1, days: { "2026-10-25": 1 } };
  const more = applyCompletion(start, "2026-10-25", 1);
  assert.deepEqual(more.days, { "2026-10-25": 2 });
  assert.equal(more.totalDone, 2);
  const gone = applyCompletion(start, "2026-10-25", -1);
  assert.deepEqual(gone.days, {});
  assert.equal(gone.totalDone, 0);
  assert.deepEqual(start.days, { "2026-10-25": 1 });
});

test("localDay uses the local calendar", () => {
  assert.equal(localDay(new Date(2026, 0, 5, 23, 30)), "2026-01-05");
});
