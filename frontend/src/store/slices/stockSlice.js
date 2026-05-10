import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  stocks: [],
  total: 0,
  currentPage: 1,
  pageSize: 100,
  selectedStock: null,
  stockDetail: null,
  filters: {
    market: '',
    search: '',
    sort: 'change_percent',
    order: 'desc',
  },
  realTimeData: [],
  lastUpdateTime: null,
  favorites: [],
  loading: false,
  error: null,
  viewSettings: {
    showFavorites: false,
    showRealTime: false,
    autoRefresh: false,
    refreshInterval: 30000,
  },
};

const stockSlice = createSlice({
  name: 'stocks',
  initialState,
  reducers: {
    setStocks: (state, action) => {
      state.stocks = action.payload.stocks || [];
      state.total = action.payload.total || 0;
      state.currentPage = action.payload.page || 1;
      state.pageSize = action.payload.limit || 100;
    },
    setSelectedStock: (state, action) => {
      state.selectedStock = action.payload;
    },
    setStockDetail: (state, action) => {
      state.stockDetail = action.payload;
    },
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    resetFilters: (state) => {
      state.filters = initialState.filters;
    },
    setRealTimeData: (state, action) => {
      state.realTimeData = action.payload || [];
      state.lastUpdateTime = new Date().toISOString();
    },
    updateStockData: (state, action) => {
      const updatedStock = action.payload;
      const index = state.stocks.findIndex((stock) => stock.symbol === updatedStock.symbol);

      if (index !== -1) {
        state.stocks[index] = { ...state.stocks[index], ...updatedStock };
      }
      if (state.selectedStock?.symbol === updatedStock.symbol) {
        state.selectedStock = { ...state.selectedStock, ...updatedStock };
      }
      if (state.stockDetail?.symbol === updatedStock.symbol) {
        state.stockDetail = { ...state.stockDetail, ...updatedStock };
      }
    },
    addFavorite: (state, action) => {
      if (!state.favorites.includes(action.payload)) {
        state.favorites.push(action.payload);
      }
    },
    removeFavorite: (state, action) => {
      state.favorites = state.favorites.filter((symbol) => symbol !== action.payload);
    },
    setFavorites: (state, action) => {
      state.favorites = action.payload || [];
    },
    setLoading: (state, action) => {
      state.loading = Boolean(action.payload);
    },
    setError: (state, action) => {
      state.error = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
    updateViewSettings: (state, action) => {
      state.viewSettings = { ...state.viewSettings, ...action.payload };
    },
    toggleShowFavorites: (state) => {
      state.viewSettings.showFavorites = !state.viewSettings.showFavorites;
    },
    toggleShowRealTime: (state) => {
      state.viewSettings.showRealTime = !state.viewSettings.showRealTime;
    },
    toggleAutoRefresh: (state) => {
      state.viewSettings.autoRefresh = !state.viewSettings.autoRefresh;
    },
    setRefreshInterval: (state, action) => {
      state.viewSettings.refreshInterval = action.payload;
    },
    resetStockState: () => initialState,
  },
});

export const {
  setStocks,
  setSelectedStock,
  setStockDetail,
  setFilters,
  resetFilters,
  setRealTimeData,
  updateStockData,
  addFavorite,
  removeFavorite,
  setFavorites,
  setLoading,
  setError,
  clearError,
  updateViewSettings,
  toggleShowFavorites,
  toggleShowRealTime,
  toggleAutoRefresh,
  setRefreshInterval,
  resetStockState,
} = stockSlice.actions;

export const selectStocks = (state) => state.stocks.stocks;
export const selectStockTotal = (state) => state.stocks.total;
export const selectCurrentPage = (state) => state.stocks.currentPage;
export const selectPageSize = (state) => state.stocks.pageSize;
export const selectSelectedStock = (state) => state.stocks.selectedStock;
export const selectStockDetail = (state) => state.stocks.stockDetail;
export const selectFilters = (state) => state.stocks.filters;
export const selectRealTimeData = (state) => state.stocks.realTimeData;
export const selectLastUpdateTime = (state) => state.stocks.lastUpdateTime;
export const selectFavorites = (state) => state.stocks.favorites;
export const selectLoading = (state) => state.stocks.loading;
export const selectError = (state) => state.stocks.error;
export const selectViewSettings = (state) => state.stocks.viewSettings;

export const selectFilteredStocks = (state) => {
  const { stocks, filters, favorites, viewSettings } = state.stocks;
  let filteredStocks = [...stocks];

  if (viewSettings.showFavorites) {
    filteredStocks = filteredStocks.filter((stock) => favorites.includes(stock.symbol));
  }
  if (filters.search) {
    const searchTerm = filters.search.toLowerCase();
    filteredStocks = filteredStocks.filter(
      (stock) =>
        stock.name?.toLowerCase().includes(searchTerm) ||
        stock.symbol?.toLowerCase().includes(searchTerm)
    );
  }
  if (filters.market) {
    filteredStocks = filteredStocks.filter((stock) => stock.market === filters.market);
  }

  filteredStocks.sort((a, b) => {
    const aValue = Number(a?.[filters.sort] ?? 0);
    const bValue = Number(b?.[filters.sort] ?? 0);
    return filters.order === 'desc' ? bValue - aValue : aValue - bValue;
  });

  return filteredStocks;
};

export const selectFavoriteStocks = (state) =>
  state.stocks.stocks.filter((stock) => state.stocks.favorites.includes(stock.symbol));

export const selectStockBySymbol = (symbol) => (state) =>
  state.stocks.stocks.find((stock) => stock.symbol === symbol);

export const selectIsFavorite = (symbol) => (state) => state.stocks.favorites.includes(symbol);

export default stockSlice.reducer;
