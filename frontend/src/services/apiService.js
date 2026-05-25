import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

const baseQuery = fetchBaseQuery({
  baseUrl: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
  prepareHeaders: (headers, { getState }) => {
    headers.set('Content-Type', 'application/json');
    const token = getState()?.auth?.token;
    if (token) {
      headers.set('authorization', `Bearer ${token}`);
    }
    return headers;
  },
});

export const apiService = createApi({
  reducerPath: 'api',
  baseQuery,
  tagTypes: ['Stock', 'Prediction', 'AI', 'System', 'User'],
  endpoints: (builder) => ({
    getStocks: builder.query({
      query: (params = {}) => ({
        url: '/api/stocks',
        params,
      }),
      providesTags: ['Stock'],
    }),
    getStockDetail: builder.query({
      query: (symbol) => `/api/stocks/${symbol}`,
      providesTags: (result, error, symbol) => [{ type: 'Stock', id: symbol }],
    }),
    getRealTimeStocks: builder.query({
      query: () => '/api/stocks/realtime',
      providesTags: ['Stock'],
    }),
    quickAnalyze: builder.mutation({
      query: (data) => ({
        url: '/api/ai/quick-analyze',
        method: 'POST',
        body: { query: data?.query || data?.text || '' },
      }),
      invalidatesTags: ['AI'],
    }),
    analyze: builder.mutation({
      query: (data) => ({
        url: '/api/ai/analyze',
        method: 'POST',
        body: { query: data?.query || data?.text || '' },
      }),
      invalidatesTags: ['AI'],
    }),
    getAIServiceStatus: builder.query({
      query: () => '/api/system/health',
      transformResponse: (response) => response?.data?.components?.ai_service || null,
      providesTags: ['AI'],
    }),
    getAIRuntimeConfig: builder.query({
      query: () => '/api/system/health',
      transformResponse: (response) => response?.data?.runtime?.ai || null,
      providesTags: ['AI'],
    }),
    predict: builder.mutation({
      query: (data) => ({
        url: '/api/predictions/predict',
        method: 'POST',
        body: {
          symbol: data?.symbol,
          horizon: data?.horizon || 5,
          up_threshold: data?.upThreshold ?? data?.up_threshold ?? 0.02,
        },
      }),
      invalidatesTags: ['Prediction'],
    }),
    backtest: builder.mutation({
      query: (data) => ({
        url: '/api/predictions/backtest',
        method: 'POST',
        body: {
          symbol: data?.symbol,
          strategy: data?.strategy || 'default',
          horizon: data?.horizon || 5,
          test_size: data?.testSize ?? data?.test_size ?? 0.2,
          up_threshold: data?.upThreshold ?? data?.up_threshold ?? 0.02,
        },
      }),
      invalidatesTags: ['Prediction'],
    }),
    trainModel: builder.mutation({
      query: (data) => ({
        url: '/api/predictions/predict',
        method: 'GET',
        params: {
          symbol: data?.symbol,
          horizon: data?.horizon || 5,
          up_threshold: data?.upThreshold ?? data?.up_threshold ?? 0.02,
        },
      }),
      invalidatesTags: ['Prediction'],
    }),
    getPredictionSnapshot: builder.query({
      query: (data = {}) => ({
        url: '/api/predictions/predict',
        params: {
          symbol: data.symbol,
          horizon: data.horizon || 5,
          up_threshold: data?.upThreshold ?? data?.up_threshold ?? 0.02,
        },
      }),
      providesTags: ['Prediction'],
    }),
    healthCheck: builder.query({
      query: () => '/health',
      providesTags: ['System'],
    }),
    getServiceStatus: builder.query({
      query: () => '/api/system/health',
      providesTags: ['System'],
    }),
    getSystemStats: builder.query({
      query: () => '/api/system/health',
      transformResponse: (response) => response?.data || null,
      providesTags: ['System'],
    }),
    forceDataRefresh: builder.mutation({
      query: () => ({
        url: '/api/stocks',
        method: 'GET',
        params: { refresh: true, limit: 20 },
      }),
      invalidatesTags: ['Stock', 'System'],
    }),
    login: builder.mutation({
      query: (credentials) => ({
        url: '/api/auth/login',
        method: 'POST',
        body: credentials,
      }),
      invalidatesTags: ['User'],
    }),
    register: builder.mutation({
      query: (userData) => ({
        url: '/api/auth/register',
        method: 'POST',
        body: userData,
      }),
      invalidatesTags: ['User'],
    }),
    refreshSession: builder.mutation({
      query: (refreshToken) => ({
        url: '/api/auth/refresh',
        method: 'POST',
        body: { refresh_token: refreshToken },
      }),
      invalidatesTags: ['User'],
    }),
    logoutSession: builder.mutation({
      query: () => ({
        url: '/api/auth/logout',
        method: 'POST',
      }),
      invalidatesTags: ['User'],
    }),
    getUserProfile: builder.query({
      query: () => '/api/user/profile',
      providesTags: ['User'],
    }),
    updateUserProfile: builder.mutation({
      query: (profile) => ({
        url: '/api/user/profile',
        method: 'PUT',
        body: { profile },
      }),
      invalidatesTags: ['User'],
    }),
    updateUserSettings: builder.mutation({
      query: (settings) => ({
        url: '/api/user/settings',
        method: 'PUT',
        body: { settings },
      }),
      invalidatesTags: ['User'],
    }),
    getAdminUsers: builder.query({
      query: () => '/api/admin/users',
      providesTags: ['User'],
    }),
    getAdminDatabaseInfo: builder.query({
      query: () => '/api/admin/database-info',
      providesTags: ['System'],
    }),
    getAdminSystemConfig: builder.query({
      query: () => '/api/admin/system-config',
      providesTags: ['System'],
    }),
    updateAdminSystemConfig: builder.mutation({
      query: (payload) => ({
        url: '/api/admin/system-config',
        method: 'PUT',
        body: payload,
      }),
      invalidatesTags: ['System'],
    }),
  }),
});

export const {
  useGetStocksQuery,
  useGetStockDetailQuery,
  useGetRealTimeStocksQuery,
  useQuickAnalyzeMutation,
  useAnalyzeMutation,
  useGetAIServiceStatusQuery,
  useGetAIRuntimeConfigQuery,
  usePredictMutation,
  useBacktestMutation,
  useTrainModelMutation,
  useGetPredictionSnapshotQuery,
  useHealthCheckQuery,
  useGetServiceStatusQuery,
  useGetSystemStatsQuery,
  useForceDataRefreshMutation,
  useLoginMutation,
  useRegisterMutation,
  useRefreshSessionMutation,
  useLogoutSessionMutation,
  useGetUserProfileQuery,
  useUpdateUserProfileMutation,
  useUpdateUserSettingsMutation,
  useGetAdminUsersQuery,
  useGetAdminDatabaseInfoQuery,
  useGetAdminSystemConfigQuery,
  useUpdateAdminSystemConfigMutation,
} = apiService;

export default apiService;

export const formatStockData = (stock = {}) => ({
  ...stock,
  current_price: Number(stock.current_price ?? stock.price ?? 0),
  change_percent: Number(stock.change_percent ?? 0),
  updated_at: stock.updated_at ? new Date(stock.updated_at).toLocaleString() : null,
  trend:
    Number(stock.change_percent ?? 0) > 0
      ? 'up'
      : Number(stock.change_percent ?? 0) < 0
      ? 'down'
      : 'flat',
});

export const formatHistoryData = (history = []) =>
  history.map((item) => ({
    ...item,
    date: item.date ? new Date(item.date).toLocaleDateString() : '',
    close_price: Number(item.close_price ?? item.close ?? 0),
    volume: Number(item.volume ?? 0),
  }));

export const formatAIResponse = (response) => {
  if (typeof response === 'string') return response;
  if (response?.response) return response.response;
  return JSON.stringify(response ?? {}, null, 2);
};

export const formatPredictionResult = (prediction = {}) => ({
  ...prediction,
  prediction: prediction.prediction === 1 ? '??' : prediction.prediction === 0 ? '??' : '??',
  confidence: Math.round(Number(prediction.confidence ?? 0) * 100),
  explanation: prediction.explanation || '????',
  created_at: new Date().toLocaleString(),
});

export const handleApiError = (error) => {
  if (error?.status === 401) return '??????????';
  if (error?.status === 403) return '????';
  if (error?.status === 404) return '???????';
  if (error?.status === 429) return '????????????';
  if (error?.status >= 500) return '???????????';
  return error?.data?.message || error?.message || '????';
};

export const retryQuery = (fn, maxRetries = 3, delay = 1000) => {
  return async (...args) => {
    let lastError;
    for (let i = 0; i < maxRetries; i += 1) {
      try {
        return await fn(...args);
      } catch (error) {
        lastError = error;
        if (i < maxRetries - 1) {
          await new Promise((resolve) => setTimeout(resolve, delay * 2 ** i));
        }
      }
    }
    throw lastError;
  };
};
