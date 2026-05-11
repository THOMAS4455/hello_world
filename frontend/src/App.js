import React, { Suspense, lazy, useEffect, useRef } from 'react';
import { Provider, useDispatch, useSelector } from 'react-redux';
import { Route, Routes, useLocation } from 'react-router-dom';
import { PersistGate } from 'redux-persist/integration/react';
import Navigation from './components/Navigation';
import RequireAuth from './components/RequireAuth';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingScreen from './components/LoadingScreen';
import NotificationContainer from './components/NotificationContainer';
import { useAppI18n } from './i18n';
import { useRefreshSessionMutation } from './services/apiService';
import { persistor, store } from './store';
import { checkTokenExpiry, logout, refreshTokenFailure, refreshTokenStart, refreshTokenSuccess } from './store/slices/authSlice';
import 'bootstrap/dist/css/bootstrap.min.css';
import './styles/App.css';

const AIChat = lazy(() => import('./pages/AIChat'));
const AdminPanel = lazy(() => import('./pages/AdminPanel'));
const Backtest = lazy(() => import('./pages/Backtest'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Home = lazy(() => import('./pages/Home'));
const Login = lazy(() => import('./pages/Login'));
const MarketSentiment = lazy(() => import('./pages/MarketSentiment'));
const Predictions = lazy(() => import('./pages/Predictions'));
const Register = lazy(() => import('./pages/Register'));
const Settings = lazy(() => import('./pages/Settings'));
const StockDetail = lazy(() => import('./pages/StockDetail'));
const TestConnection = lazy(() => import('./pages/TestConnection'));
const TestData = lazy(() => import('./pages/TestData'));
const UserProfile = lazy(() => import('./pages/UserProfile'));

const NotFound = () => {
  const { t } = useAppI18n();

  return (
    <div className="text-center mt-5">
      <h2>{t('notFoundTitle', 'Page Not Found')}</h2>
      <p className="text-muted">{t('notFoundDescription', 'Please check the URL and try again.')}</p>
    </div>
  );
};

function AppContent() {
  const location = useLocation();
  const dispatch = useDispatch();
  const language = useSelector((state) => state?.ui?.preferences?.language || 'zh-CN');
  const refreshToken = useSelector((state) => state?.auth?.refreshToken || '');
  const needsRefresh = useSelector((state) => Boolean(state?.auth?.needsRefresh));
  const isAuthenticated = useSelector((state) => Boolean(state?.auth?.isAuthenticated));
  const { t } = useAppI18n();
  const [refreshSession] = useRefreshSessionMutation();
  const refreshingRef = useRef(false);
  const isAuthPage = location.pathname === '/login' || location.pathname === '/register';

  useEffect(() => {
    document.title = t('appTitle', 'AlphaScope Research Terminal');
    document.documentElement.lang = language === 'en-US' ? 'en' : 'zh-CN';
  }, [language, t]);

  useEffect(() => {
    dispatch(checkTokenExpiry());
    const timer = setInterval(() => {
      dispatch(checkTokenExpiry());
    }, 60000);
    return () => clearInterval(timer);
  }, [dispatch]);

  useEffect(() => {
    if (!isAuthenticated || !needsRefresh || !refreshToken || refreshingRef.current) {
      return;
    }

    refreshingRef.current = true;

    const runRefresh = async () => {
      try {
        dispatch(refreshTokenStart());
        const response = await refreshSession(refreshToken).unwrap();
        if (!response?.success || !response?.data) {
          throw new Error(response?.message || 'Session refresh failed');
        }
        dispatch(refreshTokenSuccess(response.data));
      } catch (error) {
        dispatch(refreshTokenFailure(error?.data?.message || error?.message || 'Session refresh failed'));
        dispatch(logout());
      } finally {
        refreshingRef.current = false;
      }
    };

    runRefresh();
  }, [dispatch, isAuthenticated, needsRefresh, refreshSession, refreshToken]);

  return (
    <div className="App">
      {!isAuthPage && <Navigation />}

      <main className={`main-content ${isAuthPage ? 'auth-route' : ''}`}>
        <Suspense fallback={<LoadingScreen />}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/" element={<Home />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/stock/:symbol" element={<StockDetail />} />
            <Route
              path="/predictions"
              element={
                <RequireAuth>
                  <Predictions />
                </RequireAuth>
              }
            />
            <Route
              path="/backtest"
              element={
                <RequireAuth>
                  <Backtest />
                </RequireAuth>
              }
            />
            <Route
              path="/market-sentiment"
              element={
                <RequireAuth>
                  <MarketSentiment />
                </RequireAuth>
              }
            />
            <Route
              path="/ai-chat"
              element={
                <RequireAuth>
                  <AIChat />
                </RequireAuth>
              }
            />
            <Route path="/admin" element={<AdminPanel />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/profile" element={<UserProfile />} />
            <Route path="/simple-stock/:symbol" element={<StockDetail />} />
            <Route path="/enhanced" element={<Dashboard />} />
            <Route path="/enterprise" element={<Dashboard />} />
            <Route path="/test" element={<TestData />} />
            <Route path="/test-connection" element={<TestConnection />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </main>

      <NotificationContainer />
    </div>
  );
}

function App() {
  return (
    <Provider store={store}>
      <PersistGate loading={<LoadingScreen />} persistor={persistor}>
        <ErrorBoundary>
          <AppContent />
        </ErrorBoundary>
      </PersistGate>
    </Provider>
  );
}

export default App;
