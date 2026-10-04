import { useCallback, useEffect, useState } from 'react';
import stockApiService from '../services/stockApi';
import { normalizeAshareSymbol } from '../utils/stockUtils';

export const WATCHLIST_LIMIT = 20;

export function useWatchlist({ autoLoad = true } = {}) {
  const [watchlist, setWatchlist] = useState([]);
  const [config, setConfig] = useState({});
  const [loading, setLoading] = useState(Boolean(autoLoad));
  const [mutating, setMutating] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await stockApiService.getInvestmentWatchlist();
      const symbols = data?.symbols || [];
      setWatchlist(symbols);
      setConfig(data?.config || {});
      return data;
    } catch (e) {
      setError(e.message);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (autoLoad) {
      load().catch(() => {});
    }
  }, [autoLoad, load]);

  const isInWatchlist = useCallback(
    (rawSymbol) => {
      const sym = normalizeAshareSymbol(rawSymbol);
      return Boolean(sym && watchlist.includes(sym));
    },
    [watchlist],
  );

  const addSymbol = useCallback(
    async (rawSymbol) => {
      const sym = normalizeAshareSymbol(rawSymbol);
      if (!sym) {
        return { ok: false, reason: 'invalid', symbol: null };
      }
      if (watchlist.includes(sym)) {
        return { ok: false, reason: 'duplicate', symbol: sym };
      }
      if (watchlist.length >= WATCHLIST_LIMIT) {
        return { ok: false, reason: 'limit', symbol: sym };
      }

      setMutating(true);
      setError(null);
      const previous = watchlist;
      const next = [...watchlist, sym];
      setWatchlist(next);

      try {
        const data = await stockApiService.updateInvestmentWatchlist(next);
        setWatchlist(data?.symbols || next);
        setConfig(data?.config || {});
        return { ok: true, reason: 'added', symbol: sym };
      } catch (e) {
        setWatchlist(previous);
        setError(e.message);
        throw e;
      } finally {
        setMutating(false);
      }
    },
    [watchlist],
  );

  const removeSymbol = useCallback(
    async (rawSymbol) => {
      const sym = normalizeAshareSymbol(rawSymbol) || String(rawSymbol || '').trim();
      if (!sym || !watchlist.includes(sym)) {
        return { ok: false, reason: 'missing', symbol: sym };
      }

      setMutating(true);
      setError(null);
      const previous = watchlist;
      const next = watchlist.filter((s) => s !== sym);
      setWatchlist(next);

      try {
        const data = await stockApiService.updateInvestmentWatchlist(next);
        setWatchlist(data?.symbols || next);
        setConfig(data?.config || {});
        return { ok: true, reason: 'removed', symbol: sym };
      } catch (e) {
        setWatchlist(previous);
        setError(e.message);
        throw e;
      } finally {
        setMutating(false);
      }
    },
    [watchlist],
  );

  return {
    watchlist,
    config,
    setConfig,
    loading,
    mutating,
    error,
    setError,
    load,
    addSymbol,
    removeSymbol,
    isInWatchlist,
  };
}
