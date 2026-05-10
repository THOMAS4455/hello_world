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
    getAIHistory: builder.query({
      query: () => '/api/system/health',
      providesTags: ['AI'],
    }),
    getAIStats: builder.query({
      query: () => '/api/system/health',
      providesTags: ['AI'],
    }),
    trainModel: builder.mutation({
      query: (data) => ({
        url: '/api/predictions/predict',
        method: 'GET',
        params: {
          symbol: data?.symbol,
          horizon: data?.horizon || 5,
        },
      }),
      invalidatesTags: ['Prediction'],
    }),
    predict: builder.mutation({
      query: (data) => ({
        url: '/api/predictions/predict',
        method: 'GET',
        params: {
          symbol: data?.symbol,
          horizon: data?.horizon || 5,
        },
      }),
      invalidatesTags: ['Prediction'],
    }),
    backtest: builder.mutation({
      query: (data) => ({
        url: '/api/predictions/backtest',
        method: 'POST',
        params: {
          symbol: data?.symbol,
          strategy: data?.strategy || 'default',
        },
      }),
      invalidatesTags: ['Prediction'],
    }),
    getPredictionHistory: builder.query({
      query: (data = {}) => ({
        url: '/api/predictions/predict',
        params: {
          symbol: data.symbol,
          horizon: data.horizon || 5,
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
    forceDataUpdate: builder.mutation({
      query: () => ({
        url: '/api/system/health',
        method: 'GET',
      }),
      invalidatesTags: ['Stock', 'System'],
    }),
    getSystemStats: builder.query({
      query: () => '/api/system/health',
      providesTags: ['System'],
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
    getUserProfile: builder.query({
      query: () => '/api/user/profile',
      providesTags: ['User'],
    }),
    updateUserSettings: builder.mutation({
      query: (settings) => ({
        url: '/api/user/settings',
        method: 'PUT',
        body: settings,
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
  useGetAIHistoryQuery,
  useGetAIStatsQuery,
  useTrainModelMutation,
  usePredictMutation,
  useBacktestMutation,
  useGetPredictionHistoryQuery,
  useHealthCheckQuery,
  useGetServiceStatusQuery,
  useForceDataUpdateMutation,
  useGetSystemStatsQuery,
  useLoginMutation,
  useRegisterMutation,
  useGetUserProfileQuery,
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
  prediction: prediction.prediction === 1 ? '上涨' : prediction.prediction === 0 ? '下跌' : '未知',
  confidence: Math.round(Number(prediction.confidence ?? 0) * 100),
  explanation: prediction.explanation || '暂无解释',
  created_at: new Date().toLocaleString(),
});

export const handleApiError = (error) => {
  if (error?.status === 401) return '认证失败，请重新登录';
  if (error?.status === 403) return '权限不足';
  if (error?.status === 404) return '请求资源不存在';
  if (error?.status === 429) return '请求过于频繁，请稍后再试';
  if (error?.status >= 500) return '服务端错误，请稍后再试';
  return error?.data?.message || error?.message || '未知错误';
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
