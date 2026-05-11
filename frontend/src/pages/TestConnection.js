import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Spinner } from 'react-bootstrap';
import { useAppI18n } from '../i18n';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

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
      const healthResponse = await fetch(`${API_BASE_URL}/health`);
      if (healthResponse.ok) {
        const healthData = await healthResponse.json();
        testResults.health = isEnglish ? 'Backend connection is healthy' : '??????';
        testResults.healthData = healthData;
      } else {
        testResults.health = isEnglish ? 'Backend connection failed' : '??????';
      }
    } catch (err) {
      testResults.health = `${isEnglish ? 'Backend connection error' : '??????'}: ${err.message}`;
    }

    try {
      const stocksResponse = await fetch(`${API_BASE_URL}/api/stocks`);
      if (stocksResponse.ok) {
        const stocksData = await stocksResponse.json();
        testResults.stocks = isEnglish ? 'Stock API is healthy' : '?? API ??';
        testResults.stocksCount = stocksData.data?.stocks?.length || 0;
      } else {
        testResults.stocks = isEnglish ? 'Stock API failed' : '?? API ??';
      }
    } catch (err) {
      testResults.stocks = `${isEnglish ? 'Stock API error' : '?? API ??'}: ${err.message}`;
    }

    try {
      const aiResponse = await fetch(`${API_BASE_URL}/api/ai/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: isEnglish ? 'test message' : '????' }),
      });
      if (aiResponse.ok) {
        const aiData = await aiResponse.json();
        testResults.ai = isEnglish ? 'AI API is healthy' : 'AI API ??';
        testResults.aiData = aiData.success ? (isEnglish ? 'success' : '??') : isEnglish ? 'failed' : '??';
      } else {
        testResults.ai = isEnglish ? 'AI API failed' : 'AI API ??';
      }
    } catch (err) {
      testResults.ai = `${isEnglish ? 'AI API error' : 'AI API ??'}: ${err.message}`;
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
          <h4>{isEnglish ? 'Connection Test' : '????'}</h4>
        </Card.Header>
        <Card.Body>
          {status === 'checking' && (
            <div className="text-center">
              <Spinner animation="border" />
              <p className="mt-2">{isEnglish ? 'Testing connections...' : '??????...'}</p>
            </div>
          )}

          {status === 'completed' && (
            <div>
              <h5>{isEnglish ? 'Results:' : '?????'}</h5>
              <div className="mt-3">
                <p>
                  <strong>{isEnglish ? 'Backend:' : '???'}</strong> {results.health}
                </p>
                {results.healthData && (
                  <pre className="bg-light p-2 rounded">{JSON.stringify(results.healthData, null, 2)}</pre>
                )}

                <p>
                  <strong>{isEnglish ? 'Stock API:' : '?? API?'}</strong> {results.stocks}
                </p>
                {results.stocksCount !== undefined && (
                  <p>
                    {isEnglish ? `Received ${results.stocksCount} stock records` : `??? ${results.stocksCount} ?????`}
                  </p>
                )}

                <p>
                  <strong>AI API:</strong> {results.ai}
                </p>
                {results.aiData !== undefined && (
                  <p>{isEnglish ? 'AI response status:' : 'AI ?????'} {results.aiData}</p>
                )}
              </div>

              <Button variant="primary" className="mt-3" onClick={testConnection}>
                {isEnglish ? 'Run Again' : '????'}
              </Button>
            </div>
          )}

          {error && (
            <Alert variant="danger">
              <Alert.Heading>{isEnglish ? 'Test Error' : '????'}</Alert.Heading>
              <p>{error}</p>
            </Alert>
          )}
        </Card.Body>
      </Card>
    </div>
  );
};

export default TestConnection;
