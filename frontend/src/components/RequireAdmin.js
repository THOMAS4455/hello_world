import React from 'react';
import { useSelector } from 'react-redux';
import { Navigate, useLocation } from 'react-router-dom';

const RequireAdmin = ({ children }) => {
  const isAuthenticated = useSelector((state) => Boolean(state?.auth?.isAuthenticated));
  const roles = useSelector((state) => state?.auth?.roles || []);
  const location = useLocation();
  const isAdmin = Array.isArray(roles) && roles.some((role) => String(role).toLowerCase() === 'admin');

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (!isAdmin) {
    return <Navigate to="/" replace state={{ deniedFrom: location.pathname }} />;
  }

  return children;
};

export default RequireAdmin;
