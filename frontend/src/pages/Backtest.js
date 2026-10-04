import { Navigate, useLocation } from 'react-router-dom';

const BacktestRedirect = () => {
  const location = useLocation();
  return <Navigate to={`/investment/backtest${location.search}`} replace />;
};

export default BacktestRedirect;
