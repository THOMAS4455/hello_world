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
const formatDateTime = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
};

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
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingRunId, setLoadingRunId] = useState('');
  const [error, setError] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [historyItems, setHistoryItems] = useState([]);
  const preselectedStock = useMemo(() => new URLSearchParams(location.search).get('stock')?.trim() || '', [location.search]);

  useEffect(() => {
    const fetchStocks = async () => {
      setLoadingStocks(true);
      setError(null);
      try {
        const data = await stockApiService.getStocks();
        const list = Array.isArray(data) ? data.filter((s) => s && s.symbol) : [];
        if (list.length === 0) {
          throw new Error(isEnglish ? 'Stock list is empty.' : '股票列表为空。');
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

  useEffect(() => {
    const fetchHistory = async () => {
      setLoadingHistory(true);
      try {
        const rows = await stockApiService.getPredictionHistory(selectedStock, 8);
        setHistoryItems(rows);
      } catch {
        setHistoryItems([]);
      } finally {
        setLoadingHistory(false);
      }
    };
    fetchHistory();
  }, [selectedStock]);

  const handlePredict = async () => {
    if (!selectedStock) {
      setError(isEnglish ? 'Please select a stock first.' : '请先选择一只股票。');
      return;
    }

    setLoadingPrediction(true);
    setError(null);
    setPrediction(null);
    try {
      const data = await stockApiService.getStockPrediction(selectedStock, {
        horizon,
        upThreshold,
      });
      setPrediction(data);
      const rows = await stockApiService.getPredictionHistory(selectedStock, 8);
      setHistoryItems(rows);
    } catch (e) {
      setError(`${isEnglish ? 'Failed to generate prediction' : '生成预测失败'}: ${e.message}`);
    } finally {
      setLoadingPrediction(false);
    }
  };

  const handleLoadRun = async (runId) => {
    setLoadingRunId(runId);
    setError(null);
    try {
      const item = await stockApiService.getPredictionRun(runId);
      const result = item?.result || null;
      if (!result) {
        throw new Error(isEnglish ? 'Stored forecast result is unavailable.' : '存储的预测结果不可用。');
      }
      setSelectedStock(result.symbol || '');
      setHorizon(Number(result.horizon || 5));
      setUpThreshold(Number(result.up_threshold || 0.02));
      setPrediction(result);
    } catch (e) {
      setError(`${isEnglish ? 'Failed to load forecast run' : '加载预测记录失败'}: ${e.message}`);
    } finally {
      setLoadingRunId('');
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

  const layerOutputs = prediction?.layer_outputs || {};

  return (
    <div className="analysis-page">
      <section className="analysis-workspace-hero">
        <div>
          <PageLogo
            title={isEnglish ? 'Smart Forecast' : '智能预测'}
            subtitle={isEnglish ? 'Model ensemble workspace' : '多模型集成工作台'}
            glyph="P"
            tone="blue"
          />
          <div className="analysis-workspace-tag">{isEnglish ? 'Forecast Console' : '预测控制台'}</div>
          <h1>{isEnglish ? 'Multi-model forecast workspace' : '多模型预测工作台'}</h1>
          <p>
            {isEnglish
              ? 'Compare model votes, probability splits, training scores, and recent run history before moving into a trade decision.'
              : '在交易决策前，对比模型投票、概率分布、训练得分以及近期运行记录。'}
          </p>
        </div>
        <div className="analysis-workspace-actions">
          <Button
            variant="outline-light"
            onClick={() => {
              setHorizon(5);
              setUpThreshold(0.02);
            }}
          >
            {isEnglish ? 'Reset Inputs' : '重置输入'}
          </Button>
        </div>
      </section>

      <Card className="mb-4 analysis-params-card">
        <Card.Header>{isEnglish ? 'Forecast Parameters' : '预测参数'}</Card.Header>
        <Card.Body>
          <Row className="align-items-end g-3">
            <Col md={5}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'Stock' : '股票'}</Form.Label>
                <Form.Select value={selectedStock} onChange={(e) => setSelectedStock(e.target.value)} disabled={loadingStocks || stocks.length === 0}>
                  <option value="">
                    {loadingStocks
                      ? isEnglish ? 'Loading...' : '加载中...'
                      : stocks.length === 0
                      ? isEnglish ? 'No stocks available' : '暂无可用股票'
                      : isEnglish ? 'Please select a stock' : '请选择股票'}
                  </option>
                  {stocks.map((stock) => (
                    <option key={stock.symbol} value={stock.symbol}>
                      {stock.symbol} - {stock.name || (isEnglish ? 'Unknown' : '未知')}
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
                    isEnglish ? 'Run Forecast' : '运行预测'
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

      <Card className="mb-3 analysis-panel">
        <Card.Header>{isEnglish ? 'Recent Forecast Runs' : '近期预测记录'}</Card.Header>
        <Card.Body>
          {loadingHistory ? (
            <div className="text-center py-3">
              <Spinner animation="border" size="sm" />
            </div>
          ) : historyItems.length === 0 ? (
            <div className="text-muted">
              {isEnglish ? 'No stored forecast history yet for this selection.' : '当前选择下暂无已保存的预测记录。'}
            </div>
          ) : (
            <Table size="sm" bordered hover>
              <thead>
                <tr>
                  <th>{isEnglish ? 'Time' : '时间'}</th>
                  <th>{isEnglish ? 'Symbol' : '代码'}</th>
                  <th>{isEnglish ? 'Direction' : '方向'}</th>
                  <th>{isEnglish ? 'Confidence' : '置信度'}</th>
                  <th>{isEnglish ? 'Horizon' : '窗口'}</th>
                  <th>{isEnglish ? 'Action' : '操作'}</th>
                </tr>
              </thead>
              <tbody>
                {historyItems.map((item, idx) => (
                  <tr key={`${item.symbol}-${item.timestamp}-${idx}`}>
                    <td>{formatDateTime(item.created_at)}</td>
                    <td>{item.symbol}</td>
                    <td>{item.direction}</td>
                    <td>{formatPct(item.confidence)}</td>
                    <td>{item.horizon}</td>
                    <td>
                      <Button
                        size="sm"
                        variant="outline-primary"
                        onClick={() => handleLoadRun(item.id)}
                        disabled={loadingRunId === item.id}
                      >
                        {loadingRunId === item.id ? (isEnglish ? 'Loading...' : '加载中...') : isEnglish ? 'Load Run' : '加载记录'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>

      {prediction && (
        <>
          <DecisionCard
            title={isEnglish ? 'Unified Forecast Conclusion' : '统一预测结论'}
            summary={
              isEnglish
                ? `The model set gives ${prediction.symbol} a ${prediction.direction === 'up' ? 'bullish' : 'bearish'} view over the next ${prediction.horizon} days. Treat the output as a structured signal and confirm it with execution context.`
                : `模型集对未来 ${prediction.horizon} 天给出 ${prediction.symbol} 的${prediction.direction === 'up' ? '偏多' : '偏空'}判断。请将其作为结构化信号，并结合执行环境确认。`
            }
            direction={prediction.direction === 'up' ? 'bullish' : 'bearish'}
            confidence={Number(prediction.confidence || 0)}
            quality={qualityByConfidence(Number(prediction.confidence || 0))}
            riskNote={
              isEnglish
                ? 'Short-horizon forecasts can be distorted by event shocks and liquidity changes, so control position sizing and stop losses.'
                : '短周期预测容易受事件冲击和流动性变化影响，请控制仓位并设置止损。'
            }
            evidence={[
              { label: isEnglish ? 'Ensemble Up (calibrated)' : '综合上涨概率（校准后）', value: `${((layerOutputs.ensemble_up ?? avgUpProb) * 100).toFixed(1)}%` },
              { label: isEnglish ? 'Decision Threshold' : '决策阈值', value: Number(prediction.decision_threshold ?? 0.5).toFixed(2) },
              { label: isEnglish ? 'Platt Calibration' : 'Platt 校准', value: prediction.calibration_applied ? (isEnglish ? 'On' : '已启用') : isEnglish ? 'Off' : '未启用' },
              { label: isEnglish ? 'Raw Ensemble Up' : '原始综合概率', value: layerOutputs.ensemble_up_raw != null ? `${(layerOutputs.ensemble_up_raw * 100).toFixed(1)}%` : 'N/A' },
              { label: isEnglish ? 'Forecast Window' : '预测窗口', value: isEnglish ? `${prediction.horizon} days` : `${prediction.horizon} 天` },
            ]}
          />

          <Row className="g-3 mb-3">
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Direction' : '方向'}</div><div className="metric-value">{prediction.direction}<Badge bg={prediction.prediction === 1 ? 'success' : 'secondary'} className="ms-2">{prediction.prediction === 1 ? (isEnglish ? 'Up Class' : '上涨类') : isEnglish ? 'Down/Range' : '下跌/震荡'}</Badge></div></Card.Body></Card></Col>
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Confidence' : '置信度'}</div><div className="metric-value">{formatPct(prediction.confidence)}</div><ProgressBar now={(prediction.confidence || 0) * 100} /></Card.Body></Card></Col>
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Parameters' : '参数'}</div><div className="metric-value">{isEnglish ? `${prediction.horizon} days` : `${prediction.horizon} 天`}</div><div className="small text-muted">{isEnglish ? 'Threshold' : '阈值'} {prediction.up_threshold}</div></Card.Body></Card></Col>
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Symbol' : '代码'}</div><div className="metric-value">{prediction.symbol}</div></Card.Body></Card></Col>
          </Row>

          <Card className="mb-3 analysis-panel">
            <Card.Header>{isEnglish ? 'Three-Layer Outputs' : '三层模型输出'}</Card.Header>
            <Card.Body>
              <Row className="g-3">
                <Col md={3}>
                  <div className="text-muted small">{isEnglish ? 'Baseline Layer' : '基线层'}</div>
                  <div className="fw-semibold">{((layerOutputs.baseline_up ?? 0) * 100).toFixed(1)}%</div>
                </Col>
                <Col md={3}>
                  <div className="text-muted small">{isEnglish ? 'Enhanced Layer' : '增强层'}</div>
                  <div className="fw-semibold">{((layerOutputs.enhanced_up ?? 0) * 100).toFixed(1)}%</div>
                </Col>
                <Col md={3}>
                  <div className="text-muted small">{isEnglish ? 'Regime Layer' : '制度层'}</div>
                  <div className="fw-semibold">
                    {((layerOutputs.regime_up ?? 0) * 100).toFixed(1)}% ({layerOutputs.regime || 'range'})
                  </div>
                </Col>
                <Col md={3}>
                  <div className="text-muted small">{isEnglish ? 'Ensemble (calibrated)' : '综合（校准）'}</div>
                  <div className="fw-semibold">{((layerOutputs.ensemble_up ?? 0) * 100).toFixed(1)}%</div>
                  <div className="small text-muted">
                    {isEnglish ? 'Threshold' : '阈值'} {Number(prediction.decision_threshold ?? 0.5).toFixed(2)}
                  </div>
                </Col>
              </Row>
            </Card.Body>
          </Card>

          <Card className="mb-3 analysis-panel">
            <Card.Header>{isEnglish ? 'Model Probability Visualization' : '模型概率可视化'}</Card.Header>
            <Card.Body>
              {upProbRows.length === 0 ? (
                <div className="text-muted">{isEnglish ? 'No probability data available.' : '暂无概率数据。'}</div>
              ) : (
                <Plot
                  data={[
                    { x: upProbRows.map((x) => x.modelName), y: upProbRows.map((x) => x.up * 100), type: 'bar', name: isEnglish ? 'Up Probability (%)' : '上涨概率 (%)', marker: { color: '#3b82f6' } },
                    { x: upProbRows.map((x) => x.modelName), y: upProbRows.map((x) => x.down * 100), type: 'bar', name: isEnglish ? 'Down Probability (%)' : '下跌概率 (%)', marker: { color: '#94a3b8' } },
                  ]}
                  layout={{
                    barmode: 'group',
                    height: 320,
                    paper_bgcolor: '#ffffff',
                    plot_bgcolor: '#ffffff',
                    margin: { l: 40, r: 20, t: 20, b: 40 },
                    xaxis: { title: isEnglish ? 'Model' : '模型' },
                    yaxis: { title: isEnglish ? 'Probability (%)' : '概率 (%)' },
                  }}
                  config={{ responsive: true, displaylogo: false }}
                  style={{ width: '100%' }}
                />
              )}
            </Card.Body>
          </Card>

          <Card className="mb-3 analysis-panel">
            <Card.Header>{isEnglish ? 'Voting and Probability Details' : '投票与概率明细'}</Card.Header>
            <Card.Body>
              <Row className="g-3">
                <Col md={6}>
                  <h6>{isEnglish ? 'Vote Results' : '投票结果'}</h6>
                  {individualRows.length === 0 ? (
                    <div className="text-muted">{isEnglish ? 'No vote data available.' : '暂无投票数据。'}</div>
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
                    <div className="text-muted">{isEnglish ? 'No probability data available.' : '暂无概率数据。'}</div>
                  ) : (
                    <Table size="sm" bordered hover>
                      <thead><tr><th>{isEnglish ? 'Model' : '模型'}</th><th>{isEnglish ? 'Down' : '下跌'}</th><th>{isEnglish ? 'Up' : '上涨'}</th></tr></thead>
                      <tbody>{probabilityRows.map(([name, prob]) => <tr key={name}><td>{name}</td><td>{formatPct(prob?.down)}</td><td>{formatPct(prob?.up)}</td></tr>)}</tbody>
                    </Table>
                  )}
                </Col>
              </Row>
            </Card.Body>
          </Card>

          <Card className="analysis-panel">
            <Card.Header>{isEnglish ? 'Training Metrics and Explanation' : '训练指标与解释'}</Card.Header>
            <Card.Body>
              <h6>{isEnglish ? 'Cross-validation Scores' : '交叉验证得分'}</h6>
              {scoreRows.length === 0 ? (
                <div className="text-muted">{isEnglish ? 'No training scores available.' : '暂无训练得分。'}</div>
              ) : (
                <Table size="sm" bordered hover className="mb-3">
                  <thead><tr><th>{isEnglish ? 'Model' : '模型'}</th><th>{isEnglish ? 'CV Mean' : 'CV 均值'}</th><th>{isEnglish ? 'CV Std' : 'CV 标准差'}</th></tr></thead>
                  <tbody>{scoreRows.map(([name, score]) => <tr key={name}><td>{name}</td><td>{typeof score?.cv_mean === 'number' ? score.cv_mean.toFixed(4) : '-'}</td><td>{typeof score?.cv_std === 'number' ? score.cv_std.toFixed(4) : '-'}</td></tr>)}</tbody>
                </Table>
              )}
              <h6>{isEnglish ? 'Explanation' : '解释说明'}</h6>
              <div className="analysis-explanation">{prediction.explanation || (isEnglish ? 'N/A' : '暂无')}</div>
            </Card.Body>
          </Card>
        </>
      )}
    </div>
  );
};

export default Predictions;
