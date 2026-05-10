import React, { useEffect } from 'react';
import { Provider, useSelector } from 'react-redux';
import { Route, Routes, useLocation } from 'react-router-dom';
import { PersistGate } from 'redux-persist/integration/react';
import Navigation from './components/Navigation';
import RequireAuth from './components/RequireAuth';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingScreen from './components/LoadingScreen';
import NotificationContainer from './components/NotificationContainer';
import { useAppI18n } from './i18n';
import { persistor, store } from './store';
import AIChat from './pages/AIChat';
import AdminPanel from './pages/AdminPanel';
import Backtest from './pages/Backtest';
import Dashboard from './pages/Dashboard';
import Home from './pages/Home';
import Login from './pages/Login';
import MarketSentiment from './pages/MarketSentiment';
import Predictions from './pages/Predictions';
import Register from './pages/Register';
import Settings from './pages/Settings';
import StockDetail from './pages/StockDetail';
import TestConnection from './pages/TestConnection';
import TestData from './pages/TestData';
import UserProfile from './pages/UserProfile';
import 'bootstrap/dist/css/bootstrap.min.css';
import './styles/App.css';

const NotFound = () => {
  const { t } = useAppI18n();

  return (
    <div className="text-center mt-5">
      <h2>{t('notFoundTitle')}</h2>
      <p className="text-muted">{t('notFoundDescription')}</p>
    </div>
  );
};

function AppContent() {
  const location = useLocation();
  const language = useSelector((state) => state?.ui?.preferences?.language || 'zh-CN');
  const { t } = useAppI18n();
  const isAuthPage = location.pathname === '/login' || location.pathname === '/register';

  useEffect(() => {
    document.title = t('appTitle');
    document.documentElement.lang = language === 'en-US' ? 'en' : 'zh-CN';
  }, [language, t]);

  return (
    <div className="App">
      {!isAuthPage && <Navigation />}

      <main className={`main-content ${isAuthPage ? 'auth-route' : ''}`}>
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
