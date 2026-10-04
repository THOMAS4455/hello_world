export const fmtPct = (v) => (typeof v === 'number' ? `${(v * 100).toFixed(2)}%` : 'N/A');

export const fmtMoney = (v) =>
  typeof v === 'number' ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '-';

export const formatDateTime = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
};
