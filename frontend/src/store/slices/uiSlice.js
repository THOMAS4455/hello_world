import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  theme: 'light',
  sidebarCollapsed: false,
  sidebarWidth: 250,
  currentPage: '/',
  pageTitle: '股票预测系统',
  modals: {
    stockDetail: false,
    aiChat: false,
    prediction: false,
    settings: false,
  },
  notifications: [],
  globalLoading: false,
  loadingMessage: '',
  globalError: null,
  tableSettings: {
    pageSize: 20,
    pageSizeOptions: [10, 20, 50, 100],
    showBorders: true,
    showStriped: true,
    showHover: true,
    size: 'middle',
  },
  chartSettings: {
    theme: 'light',
    animation: true,
    grid: true,
    legend: true,
    tooltip: true,
  },
  preferences: {
    language: 'zh-CN',
    timezone: 'Asia/Shanghai',
    dateFormat: 'YYYY-MM-DD',
    timeFormat: 'HH:mm:ss',
    numberFormat: 'en-US',
  },
  systemStatus: {
    online: true,
    lastSyncTime: null,
    version: '3.1.0',
  },
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setTheme: (state, action) => {
      state.theme = action.payload;
      state.chartSettings.theme = action.payload;
    },
    toggleTheme: (state) => {
      state.theme = state.theme === 'light' ? 'dark' : 'light';
      state.chartSettings.theme = state.theme;
    },
    setSidebarCollapsed: (state, action) => {
      state.sidebarCollapsed = Boolean(action.payload);
      state.sidebarWidth = state.sidebarCollapsed ? 80 : 250;
    },
    toggleSidebar: (state) => {
      state.sidebarCollapsed = !state.sidebarCollapsed;
      state.sidebarWidth = state.sidebarCollapsed ? 80 : 250;
    },
    setSidebarWidth: (state, action) => {
      state.sidebarWidth = action.payload;
    },
    setCurrentPage: (state, action) => {
      state.currentPage = action.payload.path;
      state.pageTitle = action.payload.title || '股票预测系统';
    },
    setPageTitle: (state, action) => {
      state.pageTitle = action.payload;
    },
    openModal: (state, action) => {
      const modalName = action.payload;
      if (Object.prototype.hasOwnProperty.call(state.modals, modalName)) {
        state.modals[modalName] = true;
      }
    },
    closeModal: (state, action) => {
      const modalName = action.payload;
      if (Object.prototype.hasOwnProperty.call(state.modals, modalName)) {
        state.modals[modalName] = false;
      }
    },
    closeAllModals: (state) => {
      Object.keys(state.modals).forEach((key) => {
        state.modals[key] = false;
      });
    },
    addNotification: (state, action) => {
      const notification = {
        id: Date.now().toString(),
        type: action.payload.type || 'info',
        title: action.payload.title,
        message: action.payload.message,
        duration: action.payload.duration || 5000,
        timestamp: new Date().toISOString(),
        read: false,
        ...action.payload,
      };

      state.notifications.unshift(notification);
      if (state.notifications.length > 50) {
        state.notifications = state.notifications.slice(0, 50);
      }
    },
    removeNotification: (state, action) => {
      state.notifications = state.notifications.filter((notification) => notification.id !== action.payload);
    },
    markNotificationAsRead: (state, action) => {
      const notification = state.notifications.find((item) => item.id === action.payload);
      if (notification) {
        notification.read = true;
      }
    },
    markAllNotificationsAsRead: (state) => {
      state.notifications.forEach((notification) => {
        notification.read = true;
      });
    },
    clearNotifications: (state) => {
      state.notifications = [];
    },
    setGlobalLoading: (state, action) => {
      state.globalLoading = Boolean(action.payload.loading);
      state.loadingMessage = action.payload.message || '';
    },
    showGlobalLoading: (state, action) => {
      state.globalLoading = true;
      state.loadingMessage = action.payload || '加载中...';
    },
    hideGlobalLoading: (state) => {
      state.globalLoading = false;
      state.loadingMessage = '';
    },
    setGlobalError: (state, action) => {
      state.globalError = action.payload;
    },
    clearGlobalError: (state) => {
      state.globalError = null;
    },
    updateTableSettings: (state, action) => {
      state.tableSettings = { ...state.tableSettings, ...action.payload };
    },
    setTablePageSize: (state, action) => {
      state.tableSettings.pageSize = action.payload;
    },
    setTableSize: (state, action) => {
      state.tableSettings.size = action.payload;
    },
    toggleTableBorders: (state) => {
      state.tableSettings.showBorders = !state.tableSettings.showBorders;
    },
    toggleTableStriped: (state) => {
      state.tableSettings.showStriped = !state.tableSettings.showStriped;
    },
    toggleTableHover: (state) => {
      state.tableSettings.showHover = !state.tableSettings.showHover;
    },
    updateChartSettings: (state, action) => {
      state.chartSettings = { ...state.chartSettings, ...action.payload };
    },
    toggleChartAnimation: (state) => {
      state.chartSettings.animation = !state.chartSettings.animation;
    },
    toggleChartGrid: (state) => {
      state.chartSettings.grid = !state.chartSettings.grid;
    },
    toggleChartLegend: (state) => {
      state.chartSettings.legend = !state.chartSettings.legend;
    },
    toggleChartTooltip: (state) => {
      state.chartSettings.tooltip = !state.chartSettings.tooltip;
    },
    updatePreferences: (state, action) => {
      state.preferences = { ...state.preferences, ...action.payload };
    },
    setLanguage: (state, action) => {
      state.preferences.language = action.payload;
    },
    setTimezone: (state, action) => {
      state.preferences.timezone = action.payload;
    },
    setDateFormat: (state, action) => {
      state.preferences.dateFormat = action.payload;
    },
    setTimeFormat: (state, action) => {
      state.preferences.timeFormat = action.payload;
    },
    setNumberFormat: (state, action) => {
      state.preferences.numberFormat = action.payload;
    },
    setSystemStatus: (state, action) => {
      state.systemStatus = { ...state.systemStatus, ...action.payload };
    },
    setOnlineStatus: (state, action) => {
      state.systemStatus.online = Boolean(action.payload);
    },
    updateLastSyncTime: (state) => {
      state.systemStatus.lastSyncTime = new Date().toISOString();
    },
    resetUIState: () => initialState,
  },
});

export const {
  setTheme,
  toggleTheme,
  setSidebarCollapsed,
  toggleSidebar,
  setSidebarWidth,
  setCurrentPage,
  setPageTitle,
  openModal,
  closeModal,
  closeAllModals,
  addNotification,
  removeNotification,
  markNotificationAsRead,
  markAllNotificationsAsRead,
  clearNotifications,
  setGlobalLoading,
  showGlobalLoading,
  hideGlobalLoading,
  setGlobalError,
  clearGlobalError,
  updateTableSettings,
  setTablePageSize,
  setTableSize,
  toggleTableBorders,
  toggleTableStriped,
  toggleTableHover,
  updateChartSettings,
  toggleChartAnimation,
  toggleChartGrid,
  toggleChartLegend,
  toggleChartTooltip,
  updatePreferences,
  setLanguage,
  setTimezone,
  setDateFormat,
  setTimeFormat,
  setNumberFormat,
  setSystemStatus,
  setOnlineStatus,
  updateLastSyncTime,
  resetUIState,
} = uiSlice.actions;

export const selectTheme = (state) => state.ui.theme;
export const selectSidebarCollapsed = (state) => state.ui.sidebarCollapsed;
export const selectSidebarWidth = (state) => state.ui.sidebarWidth;
export const selectCurrentPage = (state) => state.ui.currentPage;
export const selectPageTitle = (state) => state.ui.pageTitle;
export const selectModals = (state) => state.ui.modals;
export const selectNotifications = (state) => state.ui.notifications;
export const selectUnreadNotifications = (state) =>
  state.ui.notifications.filter((notification) => !notification.read);
export const selectGlobalLoading = (state) => state.ui.globalLoading;
export const selectLoadingMessage = (state) => state.ui.loadingMessage;
export const selectGlobalError = (state) => state.ui.globalError;
export const selectTableSettings = (state) => state.ui.tableSettings;
export const selectChartSettings = (state) => state.ui.chartSettings;
export const selectPreferences = (state) => state.ui.preferences;
export const selectSystemStatus = (state) => state.ui.systemStatus;

export const selectIsModalOpen = (modalName) => (state) => state.ui.modals[modalName] || false;
export const selectNotificationById = (id) => (state) =>
  state.ui.notifications.find((notification) => notification.id === id);
export const selectThemeColors = (state) => {
  const isDark = state.ui.theme === 'dark';
  return {
    isDark,
    colors: {
      primary: '#1890ff',
      secondary: '#722ed1',
      success: '#52c41a',
      warning: '#faad14',
      error: '#ff4d4f',
      background: isDark ? '#141414' : '#ffffff',
      surface: isDark ? '#1f1f1f' : '#f5f5f5',
      text: isDark ? '#ffffff' : '#000000',
      textSecondary: isDark ? '#a6a6a6' : '#8c8c8c',
    },
  };
};

export default uiSlice.reducer;
