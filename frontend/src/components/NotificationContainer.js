import React from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { Toast, ToastContainer } from 'react-bootstrap';
import { useAppI18n } from '../i18n';
import { removeNotification, selectNotifications } from '../store/slices/uiSlice';

const NotificationItem = ({ notification }) => {
  const dispatch = useDispatch();
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';

  const handleClose = () => {
    dispatch(removeNotification(notification.id));
  };

  const getIcon = (type) => {
    switch (type) {
      case 'success':
        return 'bi-check-circle-fill';
      case 'error':
        return 'bi-x-circle-fill';
      case 'warning':
        return 'bi-exclamation-triangle-fill';
      case 'info':
      default:
        return 'bi-info-circle-fill';
    }
  };

  const getVariant = (type) => {
    switch (type) {
      case 'success':
        return 'success';
      case 'error':
        return 'danger';
      case 'warning':
        return 'warning';
      case 'info':
      default:
        return 'primary';
    }
  };

  return (
    <Toast
      onClose={handleClose}
      show
      delay={notification.duration || 5000}
      autohide
      className="notification-toast"
    >
      <Toast.Header className={`bg-${getVariant(notification.type)} text-white`}>
        <i className={`bi ${getIcon(notification.type)} me-2`}></i>
        <strong className="me-auto">
          {notification.title || (isEnglish ? 'System Notification' : '系统通知')}
        </strong>
        <small>{new Date(notification.timestamp).toLocaleTimeString()}</small>
      </Toast.Header>
      <Toast.Body>{notification.message}</Toast.Body>
    </Toast>
  );
};

const NotificationContainer = () => {
  const notifications = useSelector(selectNotifications);

  return (
    <ToastContainer className="notification-container" position="top-end" style={{ zIndex: 9999 }}>
      {notifications.map((notification) => (
        <NotificationItem key={notification.id} notification={notification} />
      ))}
    </ToastContainer>
  );
};

export default NotificationContainer;
