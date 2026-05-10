import React, { useEffect, useState } from 'react';
import { Card, Spinner, Alert, Button } from 'react-bootstrap';
import { useAppI18n } from '../i18n';
import { useGetStocksQuery } from '../services/apiService';

const TestData = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const { data: stocksData, isLoading, error, refetch } = useGetStocksQuery();
  const [debugInfo, setDebugInfo] = useState({});

  useEffect(() => {
    setDebugInfo({
      stocksData,
      isLoading,
      error,
      stocks: stocksData?.data?.stocks || [],
      total: stocksData?.data?.total || 0,
    });
  }, [stocksData, isLoading, error]);

  if (isLoading) {
    return (
      <div className="text-center p-4">
        <Spinner animation="border" />
        <p>{isEnglish ? 'Loading...' : '加载中...'}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <Alert variant="danger">
          <h5>{isEnglish ? 'API Error' : 'API错误'}</h5>
          <pre>{JSON.stringify(error, null, 2)}</pre>
          <Button onClick={() => refetch()}>{isEnglish ? 'Retry' : '重试'}</Button>
        </Alert>
      </div>
    );
  }

  return (
    <div className="p-4">
      <Card>
        <Card.Header>
          <h4>{isEnglish ? 'Data Test Page' : '数据测试页面'}</h4>
          <Button onClick={() => refetch()} className="float-end">{isEnglish ? 'Refresh' : '刷新'}</Button>
        </Card.Header>
        <Card.Body>
          <div className="mb-3">
            <h5>{isEnglish ? 'Debug Info:' : '调试信息:'}</h5>
            <pre style={{ fontSize: '12px', maxHeight: '200px', overflow: 'auto' }}>
              {JSON.stringify(debugInfo, null, 2)}
            </pre>
          </div>

          <div className="mb-3">
            <h5>{isEnglish ? `Stock Data (${debugInfo.total})` : `股票数据 (${debugInfo.total} 只):`}</h5>
            {debugInfo.stocks.length === 0 ? (
              <Alert variant="warning">{isEnglish ? 'No stock data available.' : '没有股票数据'}</Alert>
            ) : (
              <div>
                {debugInfo.stocks.map((stock, index) => (
                  <div key={index} className="border p-2 mb-2">
                    <strong>{stock.symbol}</strong> - {stock.name}
                    <br />
                    {isEnglish ? 'Price' : '价格'}: {stock.price}
                    <br />
                    {isEnglish ? 'Change' : '涨跌'}: {stock.change} ({stock.change_percent.toFixed(2)}%)
                    <br />
                    {isEnglish ? 'Volume' : '成交量'}: {stock.volume}
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card.Body>
      </Card>
    </div>
  );
};

export default TestData;
