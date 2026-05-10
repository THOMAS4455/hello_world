import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Form, ProgressBar, Row, Spinner, Table } from 'react-bootstrap';
import Plot from 'react-plotly.js';
import { useLocation } from 'react-router-dom';
import { useAppI18n } from '../i18n';
import DecisionCard from '../components/DecisionCard';
import PageLogo from '../components/PageLogo';
import stockApiService from '../services/stockApi';
import '../styles/PredictionBacktest.css';

const formatPct = (value) => (typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : 'N/A');

const qualityByConfidence = (c) => {
  if (c >= 0.75) return 'high';
  if (c >= 0.55) return 'medium';
  return 'low';
};

const Predictions = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const location = useLocation();
  const [stocks, setStocks] = useState([]);
  const [selectedStock, setSelectedStock] = useState('');
  const [horizon, setHorizon] = useState(5);
  const [upThreshold, setUpThreshold] = useState(0.02);
  const [loadingStocks, setLoadingStocks] = useState(false);
  const [loadingPrediction, setLoadingPrediction] = useState(false);
  const [error, setError] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const preselectedStock = useMemo(() => new URLSearchParams(location.search).get('stock')?.trim() || '', [location.search]);

  useEffect(() => {
    const fetchStocks = async () => {
      setLoadingStocks(true);
      setError(null);
      try {
        const data = await stockApiService.getStocks();
        const list = Array.isArray(data) ? data.filter((s) => s && s.symbol) : [];
        if (list.length === 0) {
          throw new Error(isEnglish ? 'Stock list is empty.' : '股票列表为空');
        }
        setStocks(list);
      } catch (e) {
        setError(`${isEnglish ? 'Failed to load stock list' : '加载股票列表失败'}: ${e.message}`);
        setStocks([]);
      } finally {
        setLoadingStocks(false);
      }
    };
    fetchStocks();
  }, [isEnglish]);

  useEffect(() => {
    if (!preselectedStock || stocks.length === 0) return;
    const matched = stocks.find((s) => String(s.symbol) === preselectedStock);
    if (matched) setSelectedStock(preselectedStock);
  }, [preselectedStock, stocks]);

  const handlePredict = async () => {
    if (!selectedStock) {
      setError(isEnglish ? 'Please select a stock first.' : '请先选择股票');
      return;
    }

    setLoadingPrediction(true);
    setError(null);
    setPrediction(null);
    try {
      const resp = await fetch(
        `http://localhost:8000/api/predictions/predict?symbol=${encodeURIComponent(selectedStock)}&horizon=${encodeURIComponent(horizon)}&up_threshold=${encodeURIComponent(upThreshold)}`
      );
      const data = await resp.json();
      if (!resp.ok || !data.success) {
        throw new Error(data.message || `${isEnglish ? 'Request failed' : '请求失败'}: ${resp.status}`);
      }
      setPrediction(data.data);
    } catch (e) {
      setError(`${isEnglish ? 'Failed to generate prediction' : '生成预测失败'}: ${e.message}`);
    } finally {
      setLoadingPrediction(false);
    }
  };

  const individualRows = useMemo(() => Object.entries(prediction?.individual_predictions || {}), [prediction]);
  const probabilityRows = useMemo(() => Object.entries(prediction?.probabilities || {}), [prediction]);
  const scoreRows = useMemo(() => Object.entries(prediction?.model_scores || {}), [prediction]);

  const upProbRows = useMemo(
    () =>
      probabilityRows.map(([modelName, prob]) => ({
        modelName,
        up: Number(prob?.up || 0),
        down: Number(prob?.down || 0),
      })),
    [probabilityRows]
  );

  const avgUpProb = useMemo(() => {
    if (upProbRows.length === 0) return 0;
    return upProbRows.reduce((sum, item) => sum + item.up, 0) / upProbRows.length;
  }, [upProbRows]);

  return (
    <div className="analysis-page">
      <div className="d-flex align-items-center justify-content-between mb-4">
        <PageLogo title="Smart Forecast" subtitle="Three-layer Model" glyph="P" tone="teal" />
        <h1 className="mb-0">{isEnglish ? 'Smart Forecast' : '智能预测'}</h1>
      </div>

      <Card className="mb-4 analysis-params-card">
        <Card.Header>{isEnglish ? 'Forecast Parameters' : '预测参数'}</Card.Header>
        <Card.Body>
          <Row className="align-items-end g-3">
            <Col md={5}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'Stock' : '股票'}</Form.Label>
                <Form.Select value={selectedStock} onChange={(e) => setSelectedStock(e.target.value)} disabled={loadingStocks || stocks.length === 0}>
                  <option value="">
                    {loadingStocks ? (isEnglish ? 'Loading...' : '加载中...') : stocks.length === 0 ? (isEnglish ? 'No stocks available' : '无可用股票') : isEnglish ? 'Please select a stock' : '请选择股票'}
                  </option>
                  {stocks.map((stock) => (
                    <option key={stock.symbol} value={stock.symbol}>
                      {stock.symbol} - {stock.name || 'Unknown'}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'Forecast Days' : '预测天数'}</Form.Label>
                <Form.Control type="number" min={1} max={30} value={horizon} onChange={(e) => setHorizon(Number(e.target.value || 5))} />
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'Up Threshold' : '上涨阈值'}</Form.Label>
                <Form.Control type="number" step="0.005" min={0} max={0.2} value={upThreshold} onChange={(e) => setUpThreshold(Number(e.target.value || 0.02))} />
              </Form.Group>
            </Col>
            <Col md={3}>
              <div className="d-flex gap-2">
                <Button variant="primary" onClick={handlePredict} disabled={loadingPrediction || loadingStocks || !selectedStock}>
                  {loadingPrediction ? (
                    <>
                      <Spinner as="span" animation="border" size="sm" className="me-2" />
                      {isEnglish ? 'Analyzing...' : '分析中...'}
                    </>
                  ) : (
                    isEnglish ? 'Run Forecast' : '开始预测'
                  )}
                </Button>
                <Button
                  variant="outline-secondary"
                  onClick={() => {
                    setHorizon(5);
                    setUpThreshold(0.02);
                  }}
                  disabled={loadingPrediction}
                >
                  {isEnglish ? 'Reset' : '重置'}
                </Button>
              </div>
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {error && <Alert variant="danger">{error}</Alert>}

      {prediction && (
        <>
          <DecisionCard
            title={isEnglish ? 'Unified Forecast Conclusion' : '预测统一结论'}
            summary={
              isEnglish
                ? `The model gives ${prediction.symbol} a ${prediction.direction === 'up' ? 'bullish' : 'bearish'} view over the next ${prediction.horizon} days. It is better to execute in tranches and watch whether the threshold break is valid.`
                : `模型对 ${prediction.symbol} 给出 ${prediction.horizon} 天窗口的${prediction.direction === 'up' ? '偏多' : '偏空'}判断，当前更适合按计划分批执行并观察阈值突破有效性。`
            }
            direction={prediction.direction === 'up' ? 'bullish' : 'bearish'}
            confidence={Number(prediction.confidence || 0)}
            quality={qualityByConfidence(Number(prediction.confidence || 0))}
            riskNote={
              isEnglish
                ? 'Short-horizon predictions are heavily influenced by breaking news and liquidity shocks, so use stop losses and position control.'
                : '短周期预测受突发新闻和流动性冲击影响较大，需配合止损和仓位控制。'
            }
            evidence={[
              { label: isEnglish ? 'Average Up Probability' : '平均上涨概率', value: `${(avgUpProb * 100).toFixed(1)}%` },
              { label: isEnglish ? 'Model Votes' : '模型投票数', value: String(individualRows.length) },
              { label: isEnglish ? 'Forecast Window' : '预测窗口', value: `${prediction.horizon} ${isEnglish ? 'days' : '天'}` },
              { label: isEnglish ? 'Up Threshold' : '上涨阈值', value: String(prediction.up_threshold) },
            ]}
          />

          <Row className="g-3 mb-3">
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Direction' : '预测方向'}</div><div className="metric-value">{prediction.direction}<Badge bg={prediction.direction === 'up' ? 'success' : 'secondary'} className="ms-2">{prediction.prediction === 1 ? (isEnglish ? 'Up Class' : '上涨类') : isEnglish ? 'Down/Range' : '下跌/震荡类'}</Badge></div></Card.Body></Card></Col>
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Confidence' : '置信度'}</div><div className="metric-value">{formatPct(prediction.confidence)}</div><ProgressBar now={(prediction.confidence || 0) * 100} /></Card.Body></Card></Col>
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Parameters' : '参数'}</div><div className="metric-value">{prediction.horizon} {isEnglish ? 'days' : '天'}</div><div className="small text-muted">{isEnglish ? 'Threshold ' : '阈值 '}{prediction.up_threshold}</div></Card.Body></Card></Col>
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Symbol' : '股票代码'}</div><div className="metric-value">{prediction.symbol}</div></Card.Body></Card></Col>
          </Row>

          <Card className="mb-3">
            <Card.Header>{isEnglish ? 'Model Probability Visualization' : '模型概率可视化'}</Card.Header>
            <Card.Body>
              {upProbRows.length === 0 ? (
                <div className="text-muted">{isEnglish ? 'No probability data available.' : '暂无概率数据'}</div>
              ) : (
                <Plot
                  data={[
                    { x: upProbRows.map((x) => x.modelName), y: upProbRows.map((x) => x.up * 100), type: 'bar', name: isEnglish ? 'Up Probability (%)' : '上涨概率(%)', marker: { color: '#0f7ae5' } },
                    { x: upProbRows.map((x) => x.modelName), y: upProbRows.map((x) => x.down * 100), type: 'bar', name: isEnglish ? 'Down Probability (%)' : '下跌概率(%)', marker: { color: '#7b8797' } },
                  ]}
                  layout={{
                    barmode: 'group',
                    height: 300,
                    margin: { l: 40, r: 20, t: 20, b: 40 },
                    xaxis: { title: isEnglish ? 'Model' : '模型' },
                    yaxis: { title: isEnglish ? 'Probability (%)' : '概率(%)' },
                  }}
                  config={{ responsive: true, displaylogo: false }}
                  style={{ width: '100%' }}
                />
              )}
            </Card.Body>
          </Card>

          <Card className="mb-3">
            <Card.Header>{isEnglish ? 'Voting and Probability Details' : '模型投票与概率明细'}</Card.Header>
            <Card.Body>
              <Row className="g-3">
                <Col md={6}>
                  <h6>{isEnglish ? 'Vote Results' : '投票结果'}</h6>
                  {individualRows.length === 0 ? (
                    <div className="text-muted">{isEnglish ? 'No vote data available.' : '无投票数据'}</div>
                  ) : (
                    <Table size="sm" bordered hover>
                      <thead><tr><th>{isEnglish ? 'Model' : '模型'}</th><th>{isEnglish ? 'Predicted Class' : '预测类别'}</th></tr></thead>
                      <tbody>{individualRows.map(([name, value]) => <tr key={name}><td>{name}</td><td>{value === 1 ? (isEnglish ? 'Up' : '上涨') : isEnglish ? 'Down/Range' : '下跌/震荡'}</td></tr>)}</tbody>
                    </Table>
                  )}
                </Col>
                <Col md={6}>
                  <h6>{isEnglish ? 'Probability Distribution' : '概率分布'}</h6>
                  {probabilityRows.length === 0 ? (
                    <div className="text-muted">{isEnglish ? 'No probability data available.' : '无概率数据'}</div>
                  ) : (
                    <Table size="sm" bordered hover>
                      <thead><tr><th>{isEnglish ? 'Model' : '模型'}</th><th>Down</th><th>Up</th></tr></thead>
                      <tbody>{probabilityRows.map(([name, prob]) => <tr key={name}><td>{name}</td><td>{formatPct(prob?.down)}</td><td>{formatPct(prob?.up)}</td></tr>)}</tbody>
                    </Table>
                  )}
                </Col>
              </Row>
            </Card.Body>
          </Card>

          <Card>
            <Card.Header>{isEnglish ? 'Training Metrics and Explanation' : '训练表现与解释'}</Card.Header>
            <Card.Body>
              <h6>{isEnglish ? 'Cross-validation Scores' : '交叉验证得分'}</h6>
              {scoreRows.length === 0 ? (
                <div className="text-muted">{isEnglish ? 'No training scores available.' : '无模型训练得分'}</div>
              ) : (
                <Table size="sm" bordered hover className="mb-3">
                  <thead><tr><th>{isEnglish ? 'Model' : '模型'}</th><th>CV Mean</th><th>CV Std</th></tr></thead>
                  <tbody>{scoreRows.map(([name, score]) => <tr key={name}><td>{name}</td><td>{typeof score?.cv_mean === 'number' ? score.cv_mean.toFixed(4) : '-'}</td><td>{typeof score?.cv_std === 'number' ? score.cv_std.toFixed(4) : '-'}</td></tr>)}</tbody>
                </Table>
              )}
              <h6>{isEnglish ? 'Explanation' : '解释文本'}</h6>
              <div className="analysis-explanation">{prediction.explanation || 'N/A'}</div>
            </Card.Body>
          </Card>
        </>
      )}
    </div>
  );
};

export default Predictions;
