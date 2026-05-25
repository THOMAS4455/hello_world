import { ASTOCKS_CONFIG } from '../config/astocks';

const SHANGHAI_TZ = ASTOCKS_CONFIG.timezone || 'Asia/Shanghai';

const getShanghaiParts = (date = new Date()) => {
  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone: SHANGHAI_TZ,
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  const parts = formatter.formatToParts(date);
  const lookup = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  const weekdayMap = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  return {
    weekday: weekdayMap[lookup.weekday] ?? 0,
    hour: Number(lookup.hour || 0),
    minute: Number(lookup.minute || 0),
    date: `${lookup.year}-${lookup.month}-${lookup.day}`,
  };
};

export const isAshareTradingSession = (date = new Date()) => {
  const { weekday, hour, minute } = getShanghaiParts(date);
  if (weekday === 0 || weekday === 6) {
    return false;
  }
  const minutes = hour * 60 + minute;
  const openMinutes = 9 * 60 + 25;
  const closeMinutes = 15 * 60;
  return minutes >= openMinutes && minutes <= closeMinutes;
};

export const getMarketAutoRefreshIntervalMs = (date = new Date()) =>
  isAshareTradingSession(date) ? 60000 : null;

export const shouldRequestLiveMarketRefresh = (force = false, date = new Date()) =>
  Boolean(force || isAshareTradingSession(date));
