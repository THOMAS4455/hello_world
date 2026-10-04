import React, { Suspense, lazy, useEffect, useRef } from 'react';
import { Provider, useDispatch, useSelector } from 'react-redux';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { PersistGate } from 'redux-persist/integration/react';
import Navigation from './components/Navigation';
import RequireAdmin from './components/RequireAdmin';
import RequireAuth from './components/RequireAuth';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingScreen from './components/LoadingScreen';
import NotificationContainer from './components/NotificationContainer';
import PredictionTaskBar from './components/PredictionTaskBar';
import { PredictionTasksProvider } from './contexts/PredictionTasksContext';
import { useAppI18n } from './i18n';
import { useRefreshSessionMutation } from './services/apiService';
import { persistor, store } from './store';
import { checkTokenExpiry, logout, refreshTokenFailure, refreshTokenStart, refreshTokenSuccess } from './store/slices/authSlice';
import 'bootstrap/dist/css/bootstrap.min.css';
import './styles/App.css';

const CHUNK_RELOAD_KEY = 'chunk_reload_once';

const lazyWithRetry = (importer, label) =>
  lazy(async () => {
    try {
      return await importer();
    } catch (error) {
      const message = String(error?.message || error || '');
      const isChunkError =
        error?.name === 'ChunkLoadError' || /Loading chunk .* failed/i.test(message);
      if (isChunkError && !sessionStorage.getItem(CHUNK_RELOAD_KEY)) {
        sessionStorage.setItem(CHUNK_RELOAD_KEY, label || 'page');
        window.location.reload();
        return new Promise(() => {});
      }
      sessionStorage.removeItem(CHUNK_RELOAD_KEY);
      throw error;
    }
  });

const AIChat = lazyWithRetry(() => import('./pages/AIChat'), 'AIChat');
const AdminPanel = lazyWithRetry(() => import('./pages/AdminPanel'), 'AdminPanel');
const Backtest = lazyWithRetry(() => import('./pages/Backtest'), 'Backtest');
const Dashboard = lazyWithRetry(() => import('./pages/Dashboard'), 'Dashboard');
const Home = lazyWithRetry(() => import('./pages/Home'), 'Home');
const Guide = lazyWithRetry(() => import('./pages/Guide'), 'Guide');
const Login = lazyWithRetry(() => import('./pages/Login'), 'Login');
const Predictions = lazyWithRetry(() => import('./pages/Predictions'), 'Predictions');
const Register = lazyWithRetry(() => import('./pages/Register'), 'Register');
const Settings = lazyWithRetry(() => import('./pages/Settings'), 'Settings');
const StockDetail = lazyWithRetry(() => import('./pages/StockDetail'), 'StockDetail');
const TestConnection = lazyWithRetry(() => import('./pages/TestConnection'), 'TestConnection');
const TestData = lazyWithRetry(() => import('./pages/TestData'), 'TestData');
const TrainingMonitor = lazyWithRetry(() => import('./pages/TrainingMonitor'), 'TrainingMonitor');
const UserProfile = lazyWithRetry(() => import('./pages/UserProfile'), 'UserProfile');
const InvestmentLayout = lazyWithRetry(() => import('./layouts/InvestmentLayout'), 'InvestmentLayout');
const PortfolioPage = lazyWithRetry(() => import('./pages/investment/PortfolioPage'), 'PortfolioPage');
const ForecastPage = lazyWithRetry(() => import('./pages/investment/ForecastPage'), 'ForecastPage');
const BacktestPage = lazyWithRetry(() => import('./pages/investment/BacktestPage'), 'BacktestPage');
const PaperPage = lazyWithRetry(() => import('./pages/investment/PaperPage'), 'PaperPage');
const InsightsPage = lazyWithRetry(() => import('./pages/investment/InsightsPage'), 'InsightsPage');
const DailyPicksPage = lazyWithRetry(() => import('./pages/investment/DailyPicksPage'), 'DailyPicksPage');
const WorkbenchPage = lazyWithRetry(() => import('./pages/investment/WorkbenchPage'), 'WorkbenchPage');

const NotFound = () => {
  const { t } = useAppI18n();

  return (
    <div className="analysis-page text-center mt-5">
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
    <PredictionTasksProvider>
      <div className="App">
        {!isAuthPage && <Navigation />}

        <main className={`main-content ds-shell ${isAuthPage ? 'auth-route' : ''}`}>
          <Suspense fallback={<LoadingScreen />}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/" element={<Home />} />
              <Route path="/guide" element={<Guide />} />
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
                path="/investment"
                element={
                  <RequireAuth>
                    <InvestmentLayout />
                  </RequireAuth>
                }
              >
                <Route index element={<Navigate to="workbench" replace />} />
                <Route path="workbench" element={<WorkbenchPage />} />
                <Route path="portfolio" element={<PortfolioPage />} />
                <Route path="forecast" element={<ForecastPage />} />
                <Route path="backtest" element={<BacktestPage />} />
                <Route path="paper" element={<PaperPage />} />
                <Route path="insights" element={<InsightsPage />} />
                <Route path="screener" element={<DailyPicksPage />} />
              </Route>
              <Route
                path="/ai-chat"
                element={
                  <RequireAuth>
                    <AIChat />
                  </RequireAuth>
                }
              />
              <Route
                path="/admin"
                element={
                  <RequireAdmin>
                    <AdminPanel />
                  </RequireAdmin>
                }
              />
              <Route
                path="/settings"
                element={
                  <RequireAuth>
                    <Settings />
                  </RequireAuth>
                }
              />
              <Route
                path="/profile"
                element={
                  <RequireAuth>
                    <UserProfile />
                  </RequireAuth>
                }
              />
              <Route path="/simple-stock/:symbol" element={<StockDetail />} />
              <Route path="/enhanced" element={<Dashboard />} />
              <Route path="/enterprise" element={<Dashboard />} />
              <Route path="/test" element={<TestData />} />
              <Route path="/test-connection" element={<TestConnection />} />
              <Route
                path="/training-monitor"
                element={
                  <RequireAdmin>
                    <TrainingMonitor />
                  </RequireAdmin>
                }
              />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </main>

        <NotificationContainer />
        <PredictionTaskBar />
      </div>
    </PredictionTasksProvider>
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
