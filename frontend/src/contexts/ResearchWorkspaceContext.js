import React, { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useAppI18n } from '../i18n';
import { useWatchlist } from '../hooks/useWatchlist';
import stockApiService from '../services/stockApi';

const ResearchWorkspaceContext = createContext(null);

export const ResearchWorkspaceProvider = ({ children }) => {
  const { language, t } = useAppI18n();
  const isEnglish = language === 'en-US';
  const location = useLocation();
  const configSaveTimer = useRef(null);
  const [pageError, setPageError] = useState(null);

  const {
    watchlist,
    config,
    setConfig,
    loading: watchlistLoading,
    mutating: watchlistMutating,
    error: watchlistError,
    setError: setWatchlistError,
    addSymbol,
    removeSymbol,
    isInWatchlist,
  } = useWatchlist();

  const urlStock = useMemo(
    () => new URLSearchParams(location.search).get('stock')?.trim() || '',
    [location.search],
  );

  const defaultStock = urlStock || watchlist[0] || '';

  const error = pageError || watchlistError;

  const setError = useCallback(
    (message) => {
      setPageError(message);
      setWatchlistError(message);
    },
    [setWatchlistError],
  );

  const clearError = useCallback(() => {
    setPageError(null);
    setWatchlistError(null);
  }, [setWatchlistError]);

  const handleConfigChange = useCallback(
    (key, value) => {
      const next = { ...config, [key]: value };
      setConfig(next);
      if (configSaveTimer.current) clearTimeout(configSaveTimer.current);
      configSaveTimer.current = setTimeout(async () => {
        try {
          const saved = await stockApiService.updatePortfolioConfig(next);
          setConfig(saved || next);
        } catch (e) {
          setError(e.message);
        }
      }, 500);
    },
    [config, setConfig, setError],
  );

  const watchlistApi = useMemo(
    () => ({
      watchlist,
      addSymbol,
      removeSymbol,
      mutating: watchlistMutating,
      isInWatchlist,
    }),
    [watchlist, addSymbol, removeSymbol, watchlistMutating, isInWatchlist],
  );

  const value = useMemo(
    () => ({
      isEnglish,
      t,
      watchlist,
      config,
      setConfig,
      watchlistLoading,
      watchlistMutating,
      error,
      setError,
      clearError,
      addSymbol,
      removeSymbol,
      handleConfigChange,
      watchlistApi,
      urlStock,
      defaultStock,
    }),
    [
      isEnglish,
      t,
      watchlist,
      config,
      setConfig,
      watchlistLoading,
      watchlistMutating,
      error,
      setError,
      clearError,
      addSymbol,
      removeSymbol,
      handleConfigChange,
      watchlistApi,
      urlStock,
      defaultStock,
    ],
  );

  return (
    <ResearchWorkspaceContext.Provider value={value}>
      {children}
    </ResearchWorkspaceContext.Provider>
  );
};

export const useResearchWorkspace = () => {
  const ctx = useContext(ResearchWorkspaceContext);
  if (!ctx) {
    throw new Error('useResearchWorkspace must be used within ResearchWorkspaceProvider');
  }
  return ctx;
};

export default ResearchWorkspaceContext;
