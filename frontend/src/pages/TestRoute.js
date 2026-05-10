import React from 'react';
import { useParams } from 'react-router-dom';
import { useAppI18n } from '../i18n';

const TestRoute = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const { symbol } = useParams();

  return (
    <div style={{ padding: '20px' }}>
      <h1>{isEnglish ? 'Route Test Page' : '路由测试页面'}</h1>
      <p>{isEnglish ? 'Current stock symbol:' : '当前股票代码:'} <strong>{symbol}</strong></p>
      <p>{isEnglish ? 'If you can see this page, the route configuration is working correctly.' : '如果你看到这个页面，说明路由配置是正确的！'}</p>
    </div>
  );
};

export default TestRoute;
