import { combineReducers, configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';
import { persistReducer, persistStore } from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import { apiService } from '../services/apiService';
import authSlice from './slices/authSlice';
import stockSlice from './slices/stockSlice';
import uiSlice from './slices/uiSlice';

const persistConfig = {
  key: 'root',
  storage,
  whitelist: ['auth', 'ui'],
  blacklist: ['api'],
};

const rootReducer = combineReducers({
  api: apiService.reducer,
  stocks: stockSlice,
  ui: uiSlice,
  auth: authSlice,
});

const persistedReducer = persistReducer(persistConfig, rootReducer);

export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [
          'persist/PERSIST',
          'persist/REHYDRATE',
          'persist/PAUSE',
          'persist/PURGE',
          'persist/REGISTER',
        ],
      },
      immutableCheck: {
        ignoredPaths: ['api'],
      },
    }).concat(apiService.middleware),
  devTools: process.env.NODE_ENV !== 'production',
});

setupListeners(store.dispatch);

export const persistor = persistStore(store);

export const getLoadingState = (state, endpoint) =>
  state.api.queries[endpoint]?.status === 'pending';

export const getErrorState = (state, endpoint) =>
  state.api.queries[endpoint]?.status === 'rejected'
    ? state.api.queries[endpoint].error
    : null;

export const getDataState = (state, endpoint) =>
  state.api.queries[endpoint]?.status === 'fulfilled'
    ? state.api.queries[endpoint].data
    : null;

export default store;
