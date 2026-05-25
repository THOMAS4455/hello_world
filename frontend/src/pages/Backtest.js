import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Form, Row, Spinner, Table } from 'react-bootstrap';
import Plot from 'react-plotly.js';
import { useLocation } from 'react-router-dom';
import { useAppI18n } from '../i18n';
import DecisionCard from '../components/DecisionCard';
import PageLogo from '../components/PageLogo';
import stockApiService from '../services/stockApi';
import '../styles/PredictionBacktest.css';

const fmtPct = (v) => (typeof v === 'number' ? `${(v * 100).toFixed(2)}%` : 'N/A');
const formatDateTime = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
};

const qualityByWalkForward = (accuracy, samples) => {
  if (accuracy >= 0.65 && samples >= 60) return 'high';
  if (accuracy >= 0.52 && samples >= 20) return 'medium';
  return 'low';
};

const Backtest = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const location = useLocation();
  const [stocks, setStocks] = useState([]);
  const [stock, setStock] = useState('');
  const [strategy, setStrategy] = useState('default');
  const [horizon, setHorizon] = useState(5);
  const [testSize, setTestSize] = useState(0.2);
  const [upThreshold, setUpThreshold] = useState(0.02);
  const [minConfidence, setMinConfidence] = useState(0);
  const [loadingStocks, setLoadingStocks] = useState(false);
  const [loadingBacktest, setLoadingBacktest] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingRunId, setLoadingRunId] = useState('');
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [historyItems, setHistoryItems] = useState([]);

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
    if (matched) setStock(preselectedStock);
  }, [preselectedStock, stocks]);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoadingHistory(true);
      try {
        const rows = await stockApiService.getBacktestHistory(stock, 8);
        setHistoryItems(rows);
      } catch {
        setHistoryItems([]);
      } finally {
        setLoadingHistory(false);
      }
    };
    fetchHistory();
  }, [stock]);

  const runBacktest = async () => {
    if (!stock) {
      setError(isEnglish ? 'Please select a stock first.' : '请先选择一只股票。');
      return;
    }

    setLoadingBacktest(true);
    setError(null);
    setResult(null);
    try {
      const data = await stockApiService.runBacktest(stock, {
        strategy,
        horizon,
        testSize,
        upThreshold,
        minConfidence,
      });
      setResult(data);
      const rows = await stockApiService.getBacktestHistory(stock, 8);
      setHistoryItems(rows);
    } catch (e) {
      setError(`${isEnglish ? 'Backtest failed' : '回测失败'}: ${e.message}`);
    } finally {
      setLoadingBacktest(false);
    }
  };

  const handleLoadRun = async (runId) => {
    setLoadingRunId(runId);
    setError(null);
    try {
      const item = await stockApiService.getBacktestRun(runId);
      const savedResult = item?.result || null;
      if (!savedResult) {
        throw new Error(isEnglish ? 'Stored backtest result is unavailable.' : '存储的回测结果不可用。');
      }
      setStock(savedResult.symbol || '');
      setStrategy(savedResult.strategy || 'default');
      setHorizon(Number(savedResult.horizon || 5));
      setTestSize(Number(savedResult.test_ratio || 0.2));
      setUpThreshold(Number(savedResult.up_threshold || 0.02));
      setResult(savedResult);
    } catch (e) {
      setError(`${isEnglish ? 'Failed to load backtest run' : '加载回测记录失败'}: ${e.message}`);
    } finally {
      setLoadingRunId('');
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
        f1: Number(metrics.f1 || 0) * 100,
      })),
    [resultRows]
  );

  const walkForward = result?.walk_forward || { accuracy: 0, samples: 0 };
  const pnl = result?.pnl_backtest || {};
  const calibration = result?.calibration || {};
  const confidence = Number(walkForward.accuracy || 0);
  const quality = qualityByWalkForward(confidence, Number(walkForward.samples || 0));
  const direction = Number(result?.improvement || 0) >= 0 ? 'bullish' : 'bearish';
  const sentimentComparison = result?.sentiment_comparison || {};
  const hasSentimentComparison = Boolean(sentimentComparison.enabled);

  const equityX = useMemo(() => {
    const len = pnl.equity_curve?.length || 0;
    return Array.from({ length: len }, (_, i) => i + 1);
  }, [pnl.equity_curve]);

  return (
    <div className="analysis-page">
      <section className="analysis-workspace-hero">
        <div>
          <PageLogo
            title={isEnglish ? 'Backtest Lab' : '回测实验室'}
            subtitle={isEnglish ? 'Validation and comparison workspace' : '验证与对比工作台'}
            glyph="B"
            tone="blue"
          />
          <div className="analysis-workspace-tag">{isEnglish ? 'Backtest Console' : '回测控制台'}</div>
          <h1>{isEnglish ? 'Model validation workspace' : '模型验证工作台'}</h1>
          <p>
            {isEnglish
              ? 'Compare classification metrics, PnL simulation, probability calibration, and walk-forward stability before trusting a signal.'
              : '在信任信号前，对比分类指标、PnL 模拟、概率校准与滚动验证稳定性。'}
          </p>
        </div>
      </section>

      <Card className="mb-4 analysis-params-card">
        <Card.Header>{isEnglish ? 'Backtest Parameters' : '回测参数'}</Card.Header>
        <Card.Body>
          <Row className="g-3 align-items-end">
            <Col md={4}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'Stock' : '股票'}</Form.Label>
                <Form.Select value={stock} onChange={(e) => setStock(e.target.value)} disabled={loadingStocks || stocks.length === 0}>
                  <option value="">
                    {loadingStocks
                      ? isEnglish ? 'Loading stocks...' : '加载股票中...'
                      : stocks.length === 0
                      ? isEnglish ? 'No stocks available' : '暂无可用股票'
                      : isEnglish ? 'Select a stock...' : '请选择股票...'}
                  </option>
                  {stocks.map((item) => (
                    <option key={item.symbol} value={item.symbol}>
                      {item.symbol} - {item.name || (isEnglish ? 'Unknown' : '未知')}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'Strategy' : '策略'}</Form.Label>
                <Form.Select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
                  <option value="default">default</option>
                  <option value="ma_cross">ma_cross</option>
                  <option value="rsi_reversion">rsi_reversion</option>
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'Horizon' : '预测窗口'}</Form.Label>
                <Form.Control type="number" min={1} max={30} value={horizon} onChange={(e) => setHorizon(Number(e.target.value || 5))} />
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'Test Size' : '测试集比例'}</Form.Label>
                <Form.Control type="number" min={0.1} max={0.5} step={0.05} value={testSize} onChange={(e) => setTestSize(Number(e.target.value || 0.2))} />
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'Up Threshold' : '上涨阈值'}</Form.Label>
                <Form.Control type="number" min={0} max={0.2} step={0.005} value={upThreshold} onChange={(e) => setUpThreshold(Number(e.target.value || 0.02))} />
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'Min Confidence (PnL)' : 'PnL 最低置信'}</Form.Label>
                <Form.Control
                  type="number"
                  min={0}
                  max={0.9}
                  step={0.05}
                  value={minConfidence}
                  onChange={(e) => setMinConfidence(Number(e.target.value || 0))}
                />
                <Form.Text muted>{isEnglish ? '0 = use decision threshold only' : '0 表示仅用决策阈值'}</Form.Text>
              </Form.Group>
            </Col>
          </Row>
          <div className="mt-3">
            <Button variant="primary" onClick={runBacktest} disabled={loadingBacktest || loadingStocks || !stock}>
              {loadingBacktest ? (
                <>
                  <Spinner as="span" animation="border" size="sm" className="me-2" />
                  {isEnglish ? 'Running...' : '运行中...'}
                </>
              ) : (
                isEnglish ? 'Run Backtest' : '运行回测'
              )}
            </Button>
          </div>
        </Card.Body>
      </Card>

      {error && <Alert variant="danger">{error}</Alert>}

      <Card className="mb-3 analysis-panel">
        <Card.Header>{isEnglish ? 'Recent Backtest Runs' : '近期回测记录'}</Card.Header>
        <Card.Body>
          {loadingHistory ? (
            <div className="text-center py-3">
              <Spinner animation="border" size="sm" />
            </div>
          ) : historyItems.length === 0 ? (
            <div className="text-muted">{isEnglish ? 'No stored backtest history yet for this selection.' : '当前选择下暂无已保存的回测记录。'}</div>
          ) : (
            <Table size="sm" bordered hover>
              <thead>
                <tr>
                  <th>{isEnglish ? 'Time' : '时间'}</th>
                  <th>{isEnglish ? 'Symbol' : '代码'}</th>
                  <th>{isEnglish ? 'Strategy' : '策略'}</th>
                  <th>{isEnglish ? 'Improvement' : '提升幅度'}</th>
                  <th>{isEnglish ? 'Walk-forward' : '滚动验证'}</th>
                  <th>{isEnglish ? 'Action' : '操作'}</th>
                </tr>
              </thead>
              <tbody>
                {historyItems.map((item, idx) => (
                  <tr key={`${item.symbol}-${item.timestamp}-${idx}`}>
                    <td>{formatDateTime(item.created_at)}</td>
                    <td>{item.symbol}</td>
                    <td>{item.strategy}</td>
                    <td>{fmtPct(item.improvement)}</td>
                    <td>{fmtPct(item.walk_forward_accuracy)}</td>
                    <td>
                      <Button size="sm" variant="outline-primary" onClick={() => handleLoadRun(item.id)} disabled={loadingRunId === item.id}>
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

      {result && (
        <>
          <DecisionCard
            title={isEnglish ? 'Backtest Summary' : '回测摘要'}
            summary={
              isEnglish
                ? `Strategy ${result.strategy} on ${result.symbol}. Improvement ${fmtPct(result.improvement)}, strategy return ${fmtPct(pnl.total_return)}, buy-hold ${fmtPct(pnl.buy_hold_return)}.`
                : `策略 ${result.strategy} @ ${result.symbol}。提升 ${fmtPct(result.improvement)}，策略收益 ${fmtPct(pnl.total_return)}，买入持有 ${fmtPct(pnl.buy_hold_return)}。`
            }
            direction={direction}
            confidence={confidence}
            quality={quality}
            riskNote={
              isEnglish
                ? 'PnL simulation excludes T+1 and limit rules. Backtests are historical diagnostics only.'
                : 'PnL 模拟未包含 T+1 与涨跌停规则。回测仅供历史诊断。'
            }
            evidence={[
              { label: isEnglish ? 'Baseline Accuracy' : '基线准确率', value: fmtPct(result.baseline_accuracy) },
              { label: isEnglish ? 'Improvement' : '提升幅度', value: fmtPct(result.improvement) },
              { label: isEnglish ? 'Strategy Return' : '策略收益', value: fmtPct(pnl.total_return) },
              { label: isEnglish ? 'Excess vs B&H' : '相对买入持有', value: fmtPct(pnl.excess_return) },
              { label: isEnglish ? 'Max Drawdown' : '最大回撤', value: fmtPct(pnl.max_drawdown) },
              { label: isEnglish ? 'Decision Threshold' : '决策阈值', value: Number(result.decision_threshold || 0.5).toFixed(2) },
            ]}
          />

          <Row className="g-3 mb-3">
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Strategy Return' : '策略收益'}</div><div className="metric-value">{fmtPct(pnl.total_return)}</div></Card.Body></Card></Col>
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Buy & Hold' : '买入持有'}</div><div className="metric-value">{fmtPct(pnl.buy_hold_return)}</div></Card.Body></Card></Col>
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Max Drawdown' : '最大回撤'}</div><div className="metric-value text-danger">{fmtPct(pnl.max_drawdown)}</div></Card.Body></Card></Col>
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Sharpe (approx)' : 'Sharpe（近似）'}</div><div className="metric-value">{Number(pnl.sharpe_ratio || 0).toFixed(2)}</div></Card.Body></Card></Col>
          </Row>

          <Card className="mb-3 analysis-panel">
            <Card.Header>{isEnglish ? 'Backtest Overview' : '回测概览'}</Card.Header>
            <Card.Body>
              <Row className="g-3">
                <Col md={3}><div className="text-muted small">{isEnglish ? 'Stock' : '股票'}</div><div className="fw-semibold">{result.symbol}</div></Col>
                <Col md={3}><div className="text-muted small">{isEnglish ? 'Strategy' : '策略'}</div><div className="fw-semibold">{result.strategy} <Badge bg="secondary">{result.period}</Badge></div></Col>
                <Col md={3}><div className="text-muted small">{isEnglish ? 'Horizon' : '预测窗口'}</div><div className="fw-semibold">{result.horizon}</div></Col>
                <Col md={3}><div className="text-muted small">{isEnglish ? 'Up Threshold' : '上涨阈值'}</div><div className="fw-semibold">{result.up_threshold}</div></Col>
              </Row>
              <Row className="g-3 mt-2">
                <Col md={3}><div className="text-muted small">{isEnglish ? 'Train Size' : '训练样本'}</div><div className="fw-semibold">{result.train_size ?? '-'}</div></Col>
                <Col md={3}><div className="text-muted small">{isEnglish ? 'Purged Embargo' : '隔离窗口'}</div><div className="fw-semibold">{result.purged_embargo ?? result.horizon} {isEnglish ? 'days' : '日'}</div></Col>
                <Col md={3}><div className="text-muted small">{isEnglish ? 'WF Method' : '滚动方法'}</div><div className="fw-semibold">{walkForward.method || 'ensemble_walk_forward'}</div></Col>
                <Col md={3}><div className="text-muted small">{isEnglish ? 'Active Days' : '持仓天数'}</div><div className="fw-semibold">{pnl.active_days ?? 0}</div></Col>
              </Row>
              <div className="mt-2 text-muted small">
                {isEnglish ? 'PnL trade signals' : 'PnL 开仓次数'}: {pnl.trade_signals ?? '-'}
                {' | '}
                {isEnglish ? 'Prob gate' : '概率门槛'}: {Number(pnl.prob_gate ?? result.decision_threshold ?? 0.5).toFixed(2)}
                {Number(pnl.min_confidence || 0) > 0 && (
                  <>
                    {' | '}
                    {isEnglish ? 'Min confidence' : '最低置信'}: {Number(pnl.min_confidence).toFixed(2)}
                  </>
                )}
              </div>
              {pnl.note && <div className="mt-2 text-muted small">{pnl.note}</div>}
            </Card.Body>
          </Card>

          {equityX.length > 0 && (
            <Card className="mb-3 analysis-panel">
              <Card.Header>{isEnglish ? 'Equity Curve (Test Period)' : '权益曲线（测试段）'}</Card.Header>
              <Card.Body>
                <Plot
                  data={[
                    { x: equityX, y: pnl.equity_curve, type: 'scatter', mode: 'lines', name: isEnglish ? 'Strategy' : '策略' },
                    { x: equityX, y: pnl.buy_hold_curve, type: 'scatter', mode: 'lines', name: isEnglish ? 'Buy & Hold' : '买入持有' },
                  ]}
                  layout={{
                    height: 320,
                    margin: { l: 40, r: 20, t: 20, b: 40 },
                    xaxis: { title: isEnglish ? 'Test Day Index' : '测试日序号' },
                    yaxis: { title: isEnglish ? 'Equity' : '权益' },
                  }}
                  config={{ responsive: true, displaylogo: false }}
                  style={{ width: '100%' }}
                />
              </Card.Body>
            </Card>
          )}

          {calibration.enabled && (
            <Card className="mb-3 analysis-panel">
              <Card.Header>{isEnglish ? 'Probability Calibration (Platt)' : '概率校准（Platt）'}</Card.Header>
              <Card.Body>
                <Row className="g-3">
                  <Col md={4}><div className="text-muted small">Brier (raw)</div><div className="fw-semibold">{Number(calibration.brier_raw || 0).toFixed(4)}</div></Col>
                  <Col md={4}><div className="text-muted small">Brier (calibrated)</div><div className="fw-semibold">{Number(calibration.brier_calibrated || 0).toFixed(4)}</div></Col>
                  <Col md={4}><div className="text-muted small">{isEnglish ? 'Improvement' : '改进'}</div><div className={`fw-semibold ${Number(calibration.brier_improvement || 0) >= 0 ? 'text-success' : 'text-danger'}`}>{Number(calibration.brier_improvement || 0).toFixed(4)}</div></Col>
                </Row>
              </Card.Body>
            </Card>
          )}

          <Card className="mb-3 analysis-panel">
            <Card.Header>{isEnglish ? 'Model Metrics' : '模型指标'}</Card.Header>
            <Card.Body>
              {modelMetricChartRows.length > 0 && (
                <Plot
                  data={[
                    { x: modelMetricChartRows.map((x) => x.name), y: modelMetricChartRows.map((x) => x.accuracy), type: 'bar', name: isEnglish ? 'Accuracy' : '准确率', marker: { color: '#3b82f6' } },
                    { x: modelMetricChartRows.map((x) => x.name), y: modelMetricChartRows.map((x) => x.f1), type: 'bar', name: 'F1', marker: { color: '#94a3b8' } },
                  ]}
                  layout={{
                    barmode: 'group',
                    height: 320,
                    paper_bgcolor: '#ffffff',
                    plot_bgcolor: '#ffffff',
                    margin: { l: 40, r: 20, t: 20, b: 40 },
                    xaxis: { title: isEnglish ? 'Model' : '模型' },
                    yaxis: { title: isEnglish ? 'Score (%)' : '得分 (%)' },
                  }}
                  config={{ responsive: true, displaylogo: false }}
                  style={{ width: '100%' }}
                />
              )}
              {resultRows.length === 0 ? (
                <div className="text-muted">{isEnglish ? 'No model metrics.' : '暂无模型指标。'}</div>
              ) : (
                <Table striped bordered hover size="sm">
                  <thead>
                    <tr>
                      <th>{isEnglish ? 'Model' : '模型'}</th>
                      <th>{isEnglish ? 'Accuracy' : '准确率'}</th>
                      <th>{isEnglish ? 'Precision' : '精确率'}</th>
                      <th>{isEnglish ? 'Recall' : '召回率'}</th>
                      <th>F1</th>
                      <th>{isEnglish ? 'Samples' : '样本数'}</th>
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

          <Card className="mb-3 analysis-panel">
            <Card.Header>{isEnglish ? 'Sentiment Fusion Comparison' : '情绪融合对比'}</Card.Header>
            <Card.Body>
              {!hasSentimentComparison ? (
                <div className="text-muted">{isEnglish ? 'Sentiment comparison is not available for this run.' : '本次运行暂无情绪对比数据。'}</div>
              ) : (
                <Row className="g-3">
                  <Col md={4}><div className="text-muted small">{isEnglish ? 'With Sentiment' : '含情绪'}</div><div className="fw-semibold">{fmtPct(sentimentComparison.with_sentiment?.accuracy)}</div></Col>
                  <Col md={4}><div className="text-muted small">{isEnglish ? 'Without Sentiment' : '不含情绪'}</div><div className="fw-semibold">{fmtPct(sentimentComparison.without_sentiment?.accuracy)}</div></Col>
                  <Col md={4}><div className="text-muted small">{isEnglish ? 'Delta' : '差值'}</div><div className="fw-semibold">{fmtPct(sentimentComparison.delta?.accuracy)}</div></Col>
                </Row>
              )}
            </Card.Body>
          </Card>

          <Card>
            <Card.Header>{isEnglish ? 'Top Feature Importance' : '特征重要性 Top'}</Card.Header>
            <Card.Body>
              {importanceRows.length === 0 ? (
                <div className="text-muted">{isEnglish ? 'No feature importance for this strategy.' : '该策略暂无特征重要性。'}</div>
              ) : (
                <Table striped bordered hover size="sm">
                  <thead>
                    <tr>
                      <th>{isEnglish ? 'Model' : '模型'}</th>
                      <th>{isEnglish ? 'Feature' : '特征'}</th>
                      <th>{isEnglish ? 'Score' : '分数'}</th>
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
