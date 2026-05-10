import React, { useState, useEffect } from 'react';
import { Card, Alert, Button, Spinner } from 'react-bootstrap';
import { useAppI18n } from '../i18n';

const TestConnection = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const [status, setStatus] = useState('checking');
  const [results, setResults] = useState({});
  const [error, setError] = useState(null);

  const testConnection = async () => {
    setStatus('checking');
    setError(null);
    const testResults = {};

    try {
      const healthResponse = await fetch('http://localhost:8000/health');
      if (healthResponse.ok) {
        const healthData = await healthResponse.json();
        testResults.health = isEnglish ? 'Backend connection is healthy' : '后端连接正常';
        testResults.healthData = healthData;
      } else {
        testResults.health = isEnglish ? 'Backend connection failed' : '后端连接失败';
      }
    } catch (err) {
      testResults.health = `${isEnglish ? 'Backend connection error' : '后端连接错误'}: ${err.message}`;
    }

    try {
      const stocksResponse = await fetch('http://localhost:8000/api/stocks');
      if (stocksResponse.ok) {
        const stocksData = await stocksResponse.json();
        testResults.stocks = isEnglish ? 'Stock API is healthy' : '股票API正常';
        testResults.stocksCount = stocksData.data?.stocks?.length || 0;
      } else {
        testResults.stocks = isEnglish ? 'Stock API failed' : '股票API失败';
      }
    } catch (err) {
      testResults.stocks = `${isEnglish ? 'Stock API error' : '股票API错误'}: ${err.message}`;
    }

    try {
      const aiResponse = await fetch('http://localhost:8000/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: isEnglish ? 'test message' : '测试消息' }),
      });
      if (aiResponse.ok) {
        const aiData = await aiResponse.json();
        testResults.ai = isEnglish ? 'AI API is healthy' : 'AI API正常';
        testResults.aiData = aiData.success ? (isEnglish ? 'success' : '成功') : isEnglish ? 'failed' : '失败';
      } else {
        testResults.ai = isEnglish ? 'AI API failed' : 'AI API失败';
      }
    } catch (err) {
      testResults.ai = `${isEnglish ? 'AI API error' : 'AI API错误'}: ${err.message}`;
    }

    setResults(testResults);
    setStatus('completed');
  };

  useEffect(() => {
    testConnection();
  }, []);

  return (
    <div className="container mt-4">
      <Card>
        <Card.Header>
          <h4>{isEnglish ? 'Connection Test' : '连接测试'}</h4>
        </Card.Header>
        <Card.Body>
          {status === 'checking' && (
            <div className="text-center">
              <Spinner animation="border" />
              <p className="mt-2">{isEnglish ? 'Testing connections...' : '正在测试连接...'}</p>
            </div>
          )}

          {status === 'completed' && (
            <div>
              <h5>{isEnglish ? 'Results:' : '测试结果:'}</h5>
              <div className="mt-3">
                <p><strong>{isEnglish ? 'Backend:' : '后端连接:'}</strong> {results.health}</p>
                {results.healthData && <pre className="bg-light p-2 rounded">{JSON.stringify(results.healthData, null, 2)}</pre>}

                <p><strong>{isEnglish ? 'Stock API:' : '股票API:'}</strong> {results.stocks}</p>
                {results.stocksCount !== undefined && (
                  <p>{isEnglish ? `Received ${results.stocksCount} stock records` : `获取到 ${results.stocksCount} 只股票数据`}</p>
                )}

                <p><strong>AI API:</strong> {results.ai}</p>
                {results.aiData !== undefined && (
                  <p>{isEnglish ? 'AI response status:' : 'AI响应状态:'} {results.aiData}</p>
                )}
              </div>

              <Button variant="primary" className="mt-3" onClick={testConnection}>
                {isEnglish ? 'Run Again' : '重新测试'}
              </Button>
            </div>
          )}

          {error && (
            <Alert variant="danger">
              <Alert.Heading>{isEnglish ? 'Test Error' : '测试错误'}</Alert.Heading>
              <p>{error}</p>
            </Alert>
          )}
        </Card.Body>
      </Card>
    </div>
  );
};

export default TestConnection;
