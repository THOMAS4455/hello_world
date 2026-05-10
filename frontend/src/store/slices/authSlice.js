import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  user: null,
  isAuthenticated: false,
  token: null,
  refreshToken: null,
  isLoading: false,
  error: null,
  permissions: [],
  roles: [],
  needsRefresh: false,
  sessionInfo: {
    loginTime: null,
    lastActivity: null,
    expiresAt: null,
    deviceId: null,
  },
  settings: {
    rememberMe: false,
    autoLogin: false,
    biometricEnabled: false,
  },
};

const resetSessionState = (state) => {
  state.user = null;
  state.isAuthenticated = false;
  state.token = null;
  state.refreshToken = null;
  state.permissions = [];
  state.roles = [];
  state.needsRefresh = false;
  state.sessionInfo = {
    loginTime: null,
    lastActivity: null,
    expiresAt: null,
    deviceId: null,
  };
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    loginStart: (state) => {
      state.isLoading = true;
      state.error = null;
    },
    loginSuccess: (state, action) => {
      const { user, token, refreshToken, permissions, roles, expiresAt, deviceId } = action.payload;
      state.user = user;
      state.token = token;
      state.refreshToken = refreshToken;
      state.permissions = permissions || [];
      state.roles = roles || [];
      state.isAuthenticated = true;
      state.isLoading = false;
      state.error = null;
      state.needsRefresh = false;
      state.sessionInfo = {
        loginTime: new Date().toISOString(),
        lastActivity: new Date().toISOString(),
        expiresAt: expiresAt || null,
        deviceId: deviceId || null,
      };
    },
    loginFailure: (state, action) => {
      state.isLoading = false;
      state.error = action.payload;
      resetSessionState(state);
    },
    logout: (state) => {
      state.error = null;
      state.isLoading = false;
      resetSessionState(state);
    },
    refreshTokenStart: (state) => {
      state.isLoading = true;
      state.error = null;
    },
    refreshTokenSuccess: (state, action) => {
      const { token, refreshToken, expiresAt } = action.payload;
      state.token = token;
      state.refreshToken = refreshToken;
      state.sessionInfo.expiresAt = expiresAt || null;
      state.sessionInfo.lastActivity = new Date().toISOString();
      state.isLoading = false;
      state.error = null;
      state.needsRefresh = false;
    },
    refreshTokenFailure: (state, action) => {
      state.isLoading = false;
      state.error = action.payload;
      resetSessionState(state);
    },
    updateUser: (state, action) => {
      state.user = { ...(state.user || {}), ...action.payload };
    },
    updatePermissions: (state, action) => {
      state.permissions = action.payload || [];
    },
    updateRoles: (state, action) => {
      state.roles = action.payload || [];
    },
    updateLastActivity: (state) => {
      state.sessionInfo.lastActivity = new Date().toISOString();
    },
    checkTokenExpiry: (state) => {
      const expiresAt = state.sessionInfo.expiresAt;
      if (!expiresAt) {
        state.needsRefresh = false;
        return;
      }

      const timeUntilExpiry = new Date(expiresAt).getTime() - Date.now();
      const fiveMinutes = 5 * 60 * 1000;

      state.needsRefresh = timeUntilExpiry > 0 && timeUntilExpiry < fiveMinutes;

      if (timeUntilExpiry <= 0) {
        resetSessionState(state);
      }
    },
    updateSettings: (state, action) => {
      state.settings = { ...state.settings, ...action.payload };
    },
    setRememberMe: (state, action) => {
      state.settings.rememberMe = Boolean(action.payload);
    },
    setAutoLogin: (state, action) => {
      state.settings.autoLogin = Boolean(action.payload);
    },
    setBiometricEnabled: (state, action) => {
      state.settings.biometricEnabled = Boolean(action.payload);
    },
    clearError: (state) => {
      state.error = null;
    },
    resetAuthState: () => initialState,
  },
});

export const {
  loginStart,
  loginSuccess,
  loginFailure,
  logout,
  refreshTokenStart,
  refreshTokenSuccess,
  refreshTokenFailure,
  updateUser,
  updatePermissions,
  updateRoles,
  updateLastActivity,
  checkTokenExpiry,
  updateSettings,
  setRememberMe,
  setAutoLogin,
  setBiometricEnabled,
  clearError,
  resetAuthState,
} = authSlice.actions;

export const selectUser = (state) => state.auth.user;
export const selectIsAuthenticated = (state) => state.auth.isAuthenticated;
export const selectToken = (state) => state.auth.token;
export const selectRefreshToken = (state) => state.auth.refreshToken;
export const selectIsLoading = (state) => state.auth.isLoading;
export const selectError = (state) => state.auth.error;
export const selectPermissions = (state) => state.auth.permissions;
export const selectRoles = (state) => state.auth.roles;
export const selectSessionInfo = (state) => state.auth.sessionInfo;
export const selectSettings = (state) => state.auth.settings;

export const selectHasPermission = (permission) => (state) =>
  state.auth.permissions.includes(permission);

export const selectHasRole = (role) => (state) => state.auth.roles.includes(role);

export const selectHasAnyPermission = (permissions) => (state) =>
  permissions.some((permission) => state.auth.permissions.includes(permission));

export const selectHasAnyRole = (roles) => (state) =>
  roles.some((role) => state.auth.roles.includes(role));

export const selectIsTokenExpired = (state) => {
  if (!state.auth.sessionInfo.expiresAt) return true;
  return Date.now() > new Date(state.auth.sessionInfo.expiresAt).getTime();
};

export const selectIsTokenExpiringSoon = (state) => {
  if (!state.auth.sessionInfo.expiresAt) return true;
  const fiveMinutes = 5 * 60 * 1000;
  return new Date(state.auth.sessionInfo.expiresAt).getTime() - Date.now() < fiveMinutes;
};

export const selectAuthStatus = (state) => ({
  isAuthenticated: state.auth.isAuthenticated,
  isLoading: state.auth.isLoading,
  error: state.auth.error,
  user: state.auth.user,
  token: state.auth.token,
  isExpired: selectIsTokenExpired(state),
  isExpiringSoon: selectIsTokenExpiringSoon(state),
});

export default authSlice.reducer;
