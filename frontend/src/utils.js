export function formatDate(value) {
  if (!value) return "Not specified";

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function daysUntil(value) {
  if (!value) return null;

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) return null;

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  return Math.round((date.getTime() - today.getTime()) / 86_400_000);
}

export function deadlineLabel(value) {
  if (!value) return "No deadline published";

  const remaining = daysUntil(value);

  if (remaining === null) return "Deadline format unrecognised";
  if (remaining < 0) return "Deadline has passed";
  if (remaining === 0) return "Closes today";
  if (remaining === 1) return "Closes tomorrow";

  return `${remaining} days remaining`;
}

export function hostLabel(url) {
  if (!url) return "";

  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

export function safeHttpUrl(value) {
  if (typeof value !== "string") return "";

  try {
    const parsed = new URL(value.trim());
    return ["http:", "https:"].includes(parsed.protocol)
      ? parsed.toString()
      : "";
  } catch {
    return "";
  }
}

export function recommendationKey(item) {
  return item?.source_url || "";
}