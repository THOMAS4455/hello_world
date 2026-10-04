import { Navigate, useLocation } from 'react-router-dom';

const PredictionsRedirect = () => {
  const location = useLocation();
  return <Navigate to={`/investment/forecast${location.search}`} replace />;
};

export default PredictionsRedirect;
