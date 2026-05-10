import React from 'react';
import { useSelector } from 'react-redux';
import { Navigate, useLocation } from 'react-router-dom';

const RequireAuth = ({ children }) => {
  const isAuthenticated = useSelector((state) => Boolean(state?.auth?.isAuthenticated));
  const location = useLocation();

  if (isAuthenticated) {
    return children;
  }

  return <Navigate to="/login" replace state={{ from: location }} />;
};

export default RequireAuth;
