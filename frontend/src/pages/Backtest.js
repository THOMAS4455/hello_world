import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Form, Row, Spinner, Table } from 'react-bootstrap';
import Plot from 'react-plotly.js';
import { useLocation } from 'react-router-dom';
import DecisionCard from '../components/DecisionCard';
import PageLogo from '../components/PageLogo';
import stockApiService from '../services/stockApi';
import '../styles/PredictionBacktest.css';

const fmtPct = (v) => (typeof v === 'number' ? `${(v * 100).toFixed(2)}%` : 'N/A');

const qualityByWalkForward = (accuracy, samples) => {
  if (accuracy >= 0.65 && samples >= 60) return 'high';
  if (accuracy >= 0.52 && samples >= 20) return 'medium';
  return 'low';
};

const Backtest = () => {
  const location = useLocation();
  const [stocks, setStocks] = useState([]);
  const [stock, setStock] = useState('');
  const [strategy, setStrategy] = useState('default');
  const [horizon, setHorizon] = useState(5);
  const [testSize, setTestSize] = useState(0.2);
  const [upThreshold, setUpThreshold] = useState(0.02);
  const [loadingStocks, setLoadingStocks] = useState(false);
  const [loadingBacktest, setLoadingBacktest] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const preselectedStock = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return (params.get('stock') || '').trim();
  }, [location.search]);

  useEffect(() => {
    const fetchStocks = async () => {
      setLoadingStocks(true);
      setError(null);
      try {
        const data = await stockApiService.getStocks();
        const list = Array.isArray(data) ? data.filter((s) => s && s.symbol) : [];
        if (list.length === 0) {
          throw new Error('stock list is empty');
        }
        setStocks(list);
      } catch (e) {
        setError(`Failed to load stocks: ${e.message}`);
        setStocks([]);
      } finally {
        setLoadingStocks(false);
      }
    };

    fetchStocks();
  }, []);

  useEffect(() => {
    if (!preselectedStock || stocks.length === 0) return;
    const matched = stocks.find((s) => String(s.symbol) === preselectedStock);
    if (matched) {
      setStock(preselectedStock);
    }
  }, [preselectedStock, stocks]);

  const runBacktest = async () => {
    if (!stock) {
      setError('Please select a stock first');
      return;
    }

    setLoadingBacktest(true);
    setError(null);
    setResult(null);
    try {
      const resp = await fetch(
        `http://localhost:8000/api/predictions/backtest?symbol=${encodeURIComponent(
          stock
        )}&strategy=${encodeURIComponent(strategy)}&horizon=${encodeURIComponent(
          horizon
        )}&test_size=${encodeURIComponent(testSize)}&up_threshold=${encodeURIComponent(upThreshold)}`,
        { method: 'POST' }
      );
      const data = await resp.json();
      if (!resp.ok || !data.success) {
        throw new Error(data.message || `request failed: ${resp.status}`);
      }
      setResult(data.data);
    } catch (e) {
      setError(`Backtest failed: ${e.message}`);
    } finally {
      setLoadingBacktest(false);
    }
  };

  const resultRows = useMemo(() => {
    const entries = Object.entries(result?.results || {});
    return entries.filter(([k, v]) => k !== 'walk_forward' && v && typeof v === 'object');
  }, [result]);

  const importanceRows = useMemo(() => {
    const all = [];
    const fi = result?.feature_importance || {};
    Object.entries(fi).forEach(([modelName, featureMap]) => {
      Object.entries(featureMap || {}).forEach(([feature, score]) => {
        all.push({ modelName, feature, score: Number(score || 0) });
      });
    });
    return all.sort((a, b) => b.score - a.score).slice(0, 12);
  }, [result]);

  const modelMetricChartRows = useMemo(
    () =>
      resultRows.map(([name, metrics]) => ({
        name,
        accuracy: Number(metrics.accuracy || 0) * 100,
        precision: Number(metrics.precision || 0) * 100,
        recall: Number(metrics.recall || 0) * 100,
        f1: Number(metrics.f1 || 0) * 100,
      })),
    [resultRows]
  );

  const walkForward = result?.walk_forward || { accuracy: 0, samples: 0 };
  const confidence = Number(walkForward.accuracy || 0);
  const quality = qualityByWalkForward(confidence, Number(walkForward.samples || 0));
  const direction = Number(result?.improvement || 0) >= 0 ? 'bullish' : 'bearish';

  const sentimentComparison = result?.sentiment_comparison || {};
  const hasSentimentComparison = Boolean(sentimentComparison.enabled);

  return (
    <div className="analysis-page">
      <div className="d-flex align-items-center justify-content-between mb-4">
        <PageLogo title="Backtest Lab" subtitle="A/B Validation" glyph="B" tone="blue" />
        <h1 className="mb-0">Backtest Analysis</h1>
      </div>

      <Card className="mb-4">
        <Card.Header>Backtest Parameters</Card.Header>
        <Card.Body>
          <Row className="g-3 align-items-end">
            <Col md={4}>
              <Form.Group>
                <Form.Label>Stock</Form.Label>
                <Form.Select
                  value={stock}
                  onChange={(e) => setStock(e.target.value)}
                  disabled={loadingStocks || stocks.length === 0}
                >
                  <option value="">
                    {loadingStocks
                      ? 'Loading stocks...'
                      : stocks.length === 0
                      ? 'No stocks available'
                      : 'Select a stock...'}
                  </option>
                  {stocks.map((item) => (
                    <option key={item.symbol} value={item.symbol}>
                      {item.symbol} - {item.name || 'Unknown'}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Group>
                <Form.Label>Strategy</Form.Label>
                <Form.Select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
                  <option value="default">default</option>
                  <option value="ma_cross">ma_cross</option>
                  <option value="rsi_reversion">rsi_reversion</option>
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Group>
                <Form.Label>Horizon</Form.Label>
                <Form.Control
                  type="number"
                  min={1}
                  max={30}
                  value={horizon}
                  onChange={(e) => setHorizon(Number(e.target.value || 5))}
                />
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Group>
                <Form.Label>Test Size</Form.Label>
                <Form.Control
                  type="number"
                  min={0.1}
                  max={0.5}
                  step={0.05}
                  value={testSize}
                  onChange={(e) => setTestSize(Number(e.target.value || 0.2))}
                />
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Group>
                <Form.Label>Up Threshold</Form.Label>
                <Form.Control
                  type="number"
                  min={0}
                  max={0.2}
                  step={0.005}
                  value={upThreshold}
                  onChange={(e) => setUpThreshold(Number(e.target.value || 0.02))}
                />
              </Form.Group>
            </Col>
          </Row>
          <div className="mt-3">
            <Button
              variant="primary"
              onClick={runBacktest}
              disabled={loadingBacktest || loadingStocks || !stock}
            >
              {loadingBacktest ? (
                <>
                  <Spinner as="span" animation="border" size="sm" className="me-2" />
                  Running...
                </>
              ) : (
                'Run Backtest'
              )}
            </Button>
          </div>
        </Card.Body>
      </Card>

      {error && <Alert variant="danger">{error}</Alert>}

      {result && (
        <>
          <DecisionCard
            title="Backtest Summary"
            summary={`Strategy ${result.strategy} finished on ${result.symbol}. Improvement vs baseline is ${fmtPct(
              result.improvement
            )}.`}
            direction={direction}
            confidence={confidence}
            quality={quality}
            riskNote="Backtest does not guarantee future returns. Validate with position and risk controls."
            evidence={[
              { label: 'Baseline Accuracy', value: fmtPct(result.baseline_accuracy) },
              { label: 'Improvement', value: fmtPct(result.improvement) },
              { label: 'Walk-forward', value: fmtPct(walkForward.accuracy) },
              { label: 'Samples', value: String(walkForward.samples || 0) },
            ]}
          />

          <Card className="mb-3">
            <Card.Header>Backtest Overview</Card.Header>
            <Card.Body>
              <Row className="g-3">
                <Col md={3}>
                  <div className="text-muted small">Stock</div>
                  <div className="fw-semibold">{result.symbol}</div>
                </Col>
                <Col md={3}>
                  <div className="text-muted small">Strategy</div>
                  <div className="fw-semibold">
                    {result.strategy} <Badge bg="secondary">{result.period}</Badge>
                  </div>
                </Col>
                <Col md={3}>
                  <div className="text-muted small">Baseline Accuracy</div>
                  <div className="fw-semibold">{fmtPct(result.baseline_accuracy)}</div>
                </Col>
                <Col md={3}>
                  <div className="text-muted small">Improvement</div>
                  <div className={`fw-semibold ${result.improvement >= 0 ? 'text-success' : 'text-danger'}`}>
                    {fmtPct(result.improvement)}
                  </div>
                </Col>
              </Row>
              <div className="mt-3 text-muted small">
                Horizon: {result.horizon} | Test Ratio: {result.test_ratio} | Threshold: {result.up_threshold}
              </div>
              {result.walk_forward?.samples > 0 && (
                <div className="mt-2">
                  Walk-forward Accuracy: <strong>{fmtPct(result.walk_forward.accuracy)}</strong> (
                  {result.walk_forward.samples} samples)
                </div>
              )}
            </Card.Body>
          </Card>

          <Card className="mb-3">
            <Card.Header>Model Metrics</Card.Header>
            <Card.Body>
              {modelMetricChartRows.length > 0 && (
                <Plot
                  data={[
                    {
                      x: modelMetricChartRows.map((x) => x.name),
                      y: modelMetricChartRows.map((x) => x.accuracy),
                      type: 'bar',
                      name: 'Accuracy',
                    },
                    {
                      x: modelMetricChartRows.map((x) => x.name),
                      y: modelMetricChartRows.map((x) => x.f1),
                      type: 'bar',
                      name: 'F1',
                    },
                  ]}
                  layout={{
                    barmode: 'group',
                    height: 320,
                    margin: { l: 40, r: 20, t: 20, b: 40 },
                    xaxis: { title: 'Model' },
                    yaxis: { title: 'Score (%)' },
                  }}
                  config={{ responsive: true, displaylogo: false }}
                  style={{ width: '100%' }}
                />
              )}
              {resultRows.length === 0 ? (
                <div className="text-muted">No model metrics.</div>
              ) : (
                <Table striped bordered hover size="sm">
                  <thead>
                    <tr>
                      <th>Model</th>
                      <th>Accuracy</th>
                      <th>Precision</th>
                      <th>Recall</th>
                      <th>F1</th>
                      <th>Samples</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resultRows.map(([name, metrics]) => (
                      <tr key={name}>
                        <td>{name}</td>
                        <td>{fmtPct(metrics.accuracy)}</td>
                        <td>{fmtPct(metrics.precision)}</td>
                        <td>{fmtPct(metrics.recall)}</td>
                        <td>{fmtPct(metrics.f1)}</td>
                        <td>{Array.isArray(metrics.predictions) ? metrics.predictions.length : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card.Body>
          </Card>

          <Card className="mb-3">
            <Card.Header>Sentiment Fusion Comparison</Card.Header>
            <Card.Body>
              {!hasSentimentComparison ? (
                <div className="text-muted">Sentiment comparison is not available for this run.</div>
              ) : (
                <>
                  <Row className="g-3 mb-3">
                    <Col md={4}>
                      <div className="text-muted small">With Sentiment Accuracy</div>
                      <div className="fw-semibold">{fmtPct(sentimentComparison.with_sentiment?.accuracy)}</div>
                    </Col>
                    <Col md={4}>
                      <div className="text-muted small">Without Sentiment Accuracy</div>
                      <div className="fw-semibold">{fmtPct(sentimentComparison.without_sentiment?.accuracy)}</div>
                    </Col>
                    <Col md={4}>
                      <div className="text-muted small">Accuracy Delta</div>
                      <div
                        className={`fw-semibold ${
                          Number(sentimentComparison.delta?.accuracy || 0) >= 0
                            ? 'text-success'
                            : 'text-danger'
                        }`}
                      >
                        {fmtPct(sentimentComparison.delta?.accuracy)}
                      </div>
                    </Col>
                  </Row>

                  <Plot
                    data={[
                      {
                        x: ['Accuracy', 'F1', 'Improvement'],
                        y: [
                          Number(sentimentComparison.with_sentiment?.accuracy || 0) * 100,
                          Number(sentimentComparison.with_sentiment?.f1 || 0) * 100,
                          Number(sentimentComparison.with_sentiment?.improvement || 0) * 100,
                        ],
                        type: 'bar',
                        name: 'With Sentiment',
                      },
                      {
                        x: ['Accuracy', 'F1', 'Improvement'],
                        y: [
                          Number(sentimentComparison.without_sentiment?.accuracy || 0) * 100,
                          Number(sentimentComparison.without_sentiment?.f1 || 0) * 100,
                          Number(sentimentComparison.without_sentiment?.improvement || 0) * 100,
                        ],
                        type: 'bar',
                        name: 'Without Sentiment',
                      },
                    ]}
                    layout={{
                      barmode: 'group',
                      height: 320,
                      margin: { l: 40, r: 20, t: 20, b: 40 },
                      yaxis: { title: 'Score (%)' },
                    }}
                    config={{ responsive: true, displaylogo: false }}
                    style={{ width: '100%' }}
                  />

                  <div className="small text-muted mt-2">
                    Feature count: with sentiment {sentimentComparison.feature_count?.with_sentiment ?? '-'},
                    without sentiment {sentimentComparison.feature_count?.without_sentiment ?? '-'},
                    sentiment-only {sentimentComparison.feature_count?.sentiment_only ?? '-'}.
                  </div>
                </>
              )}
            </Card.Body>
          </Card>

          <Card>
            <Card.Header>Top Feature Importance</Card.Header>
            <Card.Body>
              {importanceRows.length === 0 ? (
                <div className="text-muted">No feature importance available for this strategy.</div>
              ) : (
                <Table striped bordered hover size="sm">
                  <thead>
                    <tr>
                      <th>Model</th>
                      <th>Feature</th>
                      <th>Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {importanceRows.map((row, idx) => (
                      <tr key={`${row.modelName}-${row.feature}-${idx}`}>
                        <td>{row.modelName}</td>
                        <td>{row.feature}</td>
                        <td>{row.score.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card.Body>
          </Card>
        </>
      )}
    </div>
  );
};

export default Backtest;
