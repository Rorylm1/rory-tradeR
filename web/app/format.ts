export function formatMoney(value: number | null | undefined) {
  if (value === null || value === undefined) return "n/a";
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatNumber(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "n/a";
  return value.toFixed(digits);
}

export function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "n/a";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatWholeNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return "n/a";
  return new Intl.NumberFormat("en-GB", {
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatDateTime(value: string | null | undefined, includeSeconds = false) {
  if (!value) return "n/a";
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: includeSeconds ? "medium" : "short",
  }).format(new Date(value));
}
