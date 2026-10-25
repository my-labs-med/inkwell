const DAY_MS = 86400000;

export function localDay(date = new Date()) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function parseDay(day) {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

function shiftDay(day, offset) {
  return parseDay(day).getTime() + offset * DAY_MS;
}

function formatUtc(ms) {
  return new Date(ms).toISOString().slice(0, 10);
}

export function currentStreak(days, today) {
  let cursor = (days[today] || 0) > 0 ? today : formatUtc(shiftDay(today, -1));
  let streak = 0;
  while ((days[cursor] || 0) > 0) {
    streak += 1;
    cursor = formatUtc(shiftDay(cursor, -1));
  }
  return streak;
}

export function calendarGrid(today, weeks = 12) {
  const weekday = (parseDay(today).getUTCDay() + 6) % 7;
  const start = shiftDay(today, -weekday - (weeks - 1) * 7);
  const cells = [];
  for (let i = 0; i < weeks * 7; i += 1) {
    const day = formatUtc(start + i * DAY_MS);
    cells.push({ day, future: day > today });
  }
  return cells;
}

export function inkLevel(count) {
  if (!count) return 0;
  if (count === 1) return 1;
  if (count <= 3) return 2;
  if (count <= 5) return 3;
  return 4;
}

export function applyCompletion(stats, day, delta) {
  const days = { ...stats.days };
  const next = (days[day] || 0) + delta;
  if (next > 0) days[day] = next;
  else delete days[day];
  return { ...stats, days, totalDone: Math.max(0, stats.totalDone + delta) };
}
