import React, { useMemo, useRef, useState } from 'react';
import {
  Accordion,
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Form,
  Row,
  Spinner,
  Table,
} from 'react-bootstrap';
import Plot from 'react-plotly.js';
import { Link, useNavigate } from 'react-router-dom';
import StockSearchPicker from '../../components/StockSearchPicker';
import { usePredictionTasks } from '../../contexts/PredictionTasksContext';
import { useResearchWorkspace } from '../../contexts/ResearchWorkspaceContext';
import stockApiService from '../../services/stockApi';
import { computeDrawdownSeries } from '../../utils/chartUtils';
import { fmtPct } from './investmentUtils';

const PortfolioPage = () => {
  const navigate = useNavigate();
  const {
    isEnglish,
    watchlist,
    config,
    watchlistMutating,
    setError,
    clearError,
    addSymbol,
    removeSymbol,
    handleConfigChange,
  } = useResearchWorkspace();
  const { startTask, completeTask, failTask } = usePredictionTasks();

  const [searchLabel, setSearchLabel] = useState('');
  const [symbolHint, setSymbolHint] = useState(null);
  const [portfolioLoading, setPortfolioLoading] = useState(false);
  const [portfolioResult, setPortfolioResult] = useState(null);
  const activeTaskRef = useRef(null);

  const handlePickStock = async (stock) => {
    if (!stock?.symbol || watchlistMutating) return;
    setSymbolHint(null);
    clearError();
    try {
      const result = await addSymbol(stock.symbol);
      if (result.ok) {
        setSearchLabel('');
        setSymbolHint(
          isEnglish
            ? `Added ${stock.symbol} ${stock.name || ''}`.trim()
            : `已添加 ${stock.symbol} ${stock.name || ''}`.trim(),
        );
      } else if (result.reason === 'duplicate') {
        setSymbolHint(isEnglish ? `${result.symbol} is already in the watchlist.` : `${result.symbol} 已在自选池中。`);
      } else if (result.reason === 'limit') {
        setError(isEnglish ? 'Watchlist limit is 20 symbols.' : '自选池最多 20 只股票。');
      } else {
        setSymbolHint(isEnglish ? 'Invalid stock code.' : '股票代码无效。');
      }
    } catch (e) {
      setError(e.message || (isEnglish ? 'Failed to add symbol.' : '添加失败，请稍后重试。'));
    }
  };

  const handleRemoveSymbol = async (sym) => {
    clearError();
    await removeSymbol(sym);
  };

  const runPortfolioBacktest = async () => {
    if (watchlist.length === 0) {
      setError(isEnglish ? 'Add symbols to the watchlist first.' : '请先添加自选股票。');
      return;
    }
    setPortfolioLoading(true);
    clearError();
    setPortfolioResult(null);

    const taskId = startTask({
      type: 'portfolio',
      symbol: watchlist.join(','),
      params: {
        weight_mode: config.weight_mode || 'equal',
        horizon: config.horizon || 5,
        up_threshold: config.up_threshold || 0.02,
      },
      route: '/investment/portfolio',
    });
    activeTaskRef.current = taskId;

    try {
      const result = await stockApiService.runPortfolioBacktest({
        symbols: watchlist,
        weight_mode: config.weight_mode || 'equal',
        horizon: config.horizon || 5,
        up_threshold: config.up_threshold || 0.02,
        min_confidence: config.min_confidence || 0,
      });
      setPortfolioResult(result);
      completeTask(taskId, result);
    } catch (e) {
      setError(e.message);
      failTask(taskId, e.message);
    } finally {
      setPortfolioLoading(false);
      if (activeTaskRef.current === taskId) {
        activeTaskRef.current = null;
      }
    }
  };

  const portfolioChart = useMemo(() => {
    if (!portfolioResult?.equity_curve?.length) return null;
    const x = portfolioResult.equity_curve.map((_, i) => i + 1);
    return (
      <Plot
        data={[
          { x, y: portfolioResult.equity_curve, type: 'scatter', mode: 'lines', name: isEnglish ? 'Portfolio' : '组合策略' },
          { x, y: portfolioResult.buy_hold_curve, type: 'scatter', mode: 'lines', name: isEnglish ? 'Equal-weight B&H' : '等权买入持有' },
        ]}
        layout={{
          height: 340,
          margin: { l: 40, r: 20, t: 20, b: 40 },
          xaxis: { title: isEnglish ? 'Test Day' : '测试日' },
          yaxis: { title: isEnglish ? 'Equity' : '权益' },
        }}
        config={{ responsive: true, displaylogo: false }}
        style={{ width: '100%' }}
        useResizeHandler
      />
    );
  }, [portfolioResult, isEnglish]);

  const portfolioDrawdownChart = useMemo(() => {
    const curve = portfolioResult?.equity_curve;
    if (!curve?.length) return null;
    const x = curve.map((_, i) => i + 1);
    const dd = computeDrawdownSeries(curve);
    return (
      <Plot
        data={[{ x, y: dd, type: 'scatter', mode: 'lines', fill: 'tozeroy', name: isEnglish ? 'Drawdown' : '回撤' }]}
        layout={{
          height: 220,
          margin: { l: 40, r: 20, t: 10, b: 40 },
          yaxis: { title: isEnglish ? 'Drawdown' : '回撤', tickformat: '.1%' },
        }}
        config={{ responsive: true, displaylogo: false }}
        style={{ width: '100%' }}
        useResizeHandler
      />
    );
  }, [portfolioResult, isEnglish]);

  return (
    <>
      <Card className="investment-panel mb-3">
        <Card.Header className="investment-panel-header">
          <span>{isEnglish ? 'Watchlist' : '自选池'}</span>
          <Badge bg="light" text="dark">
            {watchlist.length} / 20
          </Badge>
        </Card.Header>
        <Card.Body>
          <div className="investment-watchlist-toolbar">
            <Form.Group className="investment-watchlist-search">
              <Form.Label>{isEnglish ? 'Search and add' : '搜索并添加'}</Form.Label>
              <StockSearchPicker
                value={searchLabel}
                onChange={(label) => {
                  setSearchLabel(label);
                  if (symbolHint) setSymbolHint(null);
                }}
                onSelect={handlePickStock}
                disabled={watchlistMutating || watchlist.length >= 20}
                isEnglish={isEnglish}
                excludeSymbols={watchlist}
                hint={
                  isEnglish
                    ? 'Pick a result to add instantly. You can also add from Dashboard or Forecast.'
                    : '从下拉结果中选择即可加入。也可在仪表盘或预测页一键加入自选。'
                }
              />
              {symbolHint && (
                <Form.Text className={symbolHint.includes('已添加') || symbolHint.includes('Added') ? 'text-success' : 'text-danger'}>
                  {symbolHint}
                </Form.Text>
              )}
            </Form.Group>
            <div className="investment-watchlist-actions">
              <Button variant="primary" onClick={runPortfolioBacktest} disabled={portfolioLoading || watchlist.length === 0}>
                {portfolioLoading ? <Spinner size="sm" className="me-2" /> : null}
                {isEnglish ? 'Run portfolio backtest' : '运行组合回测'}
              </Button>
              <Button variant="outline-secondary" as={Link} to="/investment/paper" disabled={watchlist.length === 0}>
                {isEnglish ? 'Paper twin' : '模拟盘'}
              </Button>
            </div>
          </div>

          <div className="investment-watchlist-chips">
            {watchlist.length === 0 ? (
              <Alert variant="light" className="mb-0 border">
                {isEnglish
                  ? 'No symbols yet. Search above, or open Dashboard / Forecast to add stocks.'
                  : '暂无自选。可在上方搜索添加，或前往仪表盘 / 预测页一键加入自选。'}
              </Alert>
            ) : (
              watchlist.map((sym) => (
                <span className="investment-symbol-chip" key={sym}>
                  <strong>{sym}</strong>
                  <button type="button" aria-label="remove" onClick={() => handleRemoveSymbol(sym)} disabled={watchlistMutating}>
                    ×
                  </button>
                  <Button
                    size="sm"
                    variant="link"
                    className="p-0 ms-1"
                    onClick={() => navigate(`/investment/forecast?stock=${sym}`)}
                  >
                    {isEnglish ? 'Forecast' : '预测'}
                  </Button>
                  <Button
                    size="sm"
                    variant="link"
                    className="p-0"
                    onClick={() => navigate(`/investment/backtest?stock=${sym}`)}
                  >
                    {isEnglish ? 'Backtest' : '回测'}
                  </Button>
                </span>
              ))
            )}
          </div>

          {watchlist.length > (config.max_symbols || 10) && (
            <Alert variant="warning" className="mb-3">
              {isEnglish
                ? `Backtest/paper uses first ${config.max_symbols || 10} symbols only.`
                : `回测/模拟盘仅使用前 ${config.max_symbols || 10} 只标的。`}
            </Alert>
          )}

          <Accordion className="investment-settings-accordion">
            <Accordion.Item eventKey="0">
              <Accordion.Header>{isEnglish ? 'Portfolio settings (advanced)' : '组合设置（高级参数）'}</Accordion.Header>
              <Accordion.Body>
                <Row className="g-3 mb-3">
                  <Col md={3}>
                    <Form.Label>{isEnglish ? 'Risk level' : '风险偏好'}</Form.Label>
                    <Form.Select value={config.risk_level || 'balanced'} onChange={(e) => handleConfigChange('risk_level', e.target.value)}>
                      <option value="conservative">{isEnglish ? 'Conservative' : '保守'}</option>
                      <option value="balanced">{isEnglish ? 'Balanced' : '均衡'}</option>
                      <option value="aggressive">{isEnglish ? 'Aggressive' : '激进'}</option>
                    </Form.Select>
                  </Col>
                  <Col md={3}>
                    <Form.Label>{isEnglish ? 'Initial capital' : '初始资金'}</Form.Label>
                    <Form.Control type="number" min={10000} value={config.initial_capital ?? 100000} onChange={(e) => handleConfigChange('initial_capital', Number(e.target.value || 100000))} />
                  </Col>
                  <Col md={3}>
                    <Form.Label>{isEnglish ? 'Max position %' : '单票上限'}</Form.Label>
                    <Form.Control type="number" step="0.05" min={0.05} max={0.5} value={config.max_position_pct ?? 0.25} onChange={(e) => handleConfigChange('max_position_pct', Number(e.target.value || 0.25))} />
                  </Col>
                  <Col md={3}>
                    <Form.Label>{isEnglish ? 'Max symbols' : '最大标的数'}</Form.Label>
                    <Form.Control type="number" min={1} max={20} value={config.max_symbols ?? 10} onChange={(e) => handleConfigChange('max_symbols', Number(e.target.value || 10))} />
                  </Col>
                </Row>
                <Row className="g-3">
                  <Col md={3}>
                    <Form.Label>{isEnglish ? 'Weight mode' : '权重模式'}</Form.Label>
                    <Form.Select value={config.weight_mode || 'equal'} onChange={(e) => handleConfigChange('weight_mode', e.target.value)}>
                      <option value="equal">{isEnglish ? 'Equal weight' : '等权'}</option>
                      <option value="signal">{isEnglish ? 'Signal weighted' : '信号加权'}</option>
                    </Form.Select>
                  </Col>
                  <Col md={2}>
                    <Form.Label>{isEnglish ? 'Horizon' : '窗口'}</Form.Label>
                    <Form.Control type="number" min={1} max={30} value={config.horizon || 5} onChange={(e) => handleConfigChange('horizon', Number(e.target.value || 5))} />
                  </Col>
                  <Col md={2}>
                    <Form.Label>{isEnglish ? 'Up threshold' : '上涨阈值'}</Form.Label>
                    <Form.Control type="number" step="0.005" value={config.up_threshold ?? 0.02} onChange={(e) => handleConfigChange('up_threshold', Number(e.target.value || 0.02))} />
                  </Col>
                  <Col md={2}>
                    <Form.Label>{isEnglish ? 'Min confidence' : '最低置信'}</Form.Label>
                    <Form.Control type="number" step="0.05" min={0} max={0.9} value={config.min_confidence ?? 0} onChange={(e) => handleConfigChange('min_confidence', Number(e.target.value || 0))} />
                  </Col>
                  <Col md={3}>
                    <Form.Label>{isEnglish ? 'Label mode' : '标签模式'}</Form.Label>
                    <Form.Select value={config.label_mode || 'fixed_horizon'} onChange={(e) => handleConfigChange('label_mode', e.target.value)}>
                      <option value="fixed_horizon">{isEnglish ? 'Fixed horizon' : '固定窗口'}</option>
                      <option value="triple_barrier">{isEnglish ? 'Triple barrier' : '三重屏障'}</option>
                    </Form.Select>
                  </Col>
                  <Col md={12} className="d-flex align-items-center">
                    <Form.Check
                      type="switch"
                      label={isEnglish ? 'Auto advance paper account daily' : '每日自动推进模拟盘'}
                      checked={Boolean(config.auto_advance_paper)}
                      onChange={(e) => handleConfigChange('auto_advance_paper', e.target.checked)}
                    />
                  </Col>
                </Row>
              </Accordion.Body>
            </Accordion.Item>
          </Accordion>
        </Card.Body>
      </Card>

      {portfolioResult && (
        <>
          <div className="ds-metrics-grid mb-3">
            <div className="investment-metric-card">
              <div className="investment-metric-label">{isEnglish ? 'Portfolio return' : '组合收益'}</div>
              <div className="investment-metric-value">{fmtPct(portfolioResult.portfolio_return)}</div>
            </div>
            <div className="investment-metric-card">
              <div className="investment-metric-label">{isEnglish ? 'Sharpe' : '夏普比率'}</div>
              <div className="investment-metric-value">{portfolioResult.metrics?.strategy?.sharpe_ratio ?? '-'}</div>
            </div>
            <div className="investment-metric-card">
              <div className="investment-metric-label">{isEnglish ? 'Max drawdown' : '最大回撤'}</div>
              <div className="investment-metric-value">{fmtPct(portfolioResult.metrics?.strategy?.max_drawdown)}</div>
            </div>
            <div className="investment-metric-card">
              <div className="investment-metric-label">{isEnglish ? 'Win rate' : '胜率'}</div>
              <div className="investment-metric-value">{fmtPct(portfolioResult.metrics?.strategy?.win_rate)}</div>
            </div>
          </div>
          <Card className="investment-panel mb-3">
            <Card.Header>{isEnglish ? 'Portfolio equity curve' : '组合权益曲线'}</Card.Header>
            <Card.Body>
              {portfolioChart}
              {portfolioDrawdownChart && (
                <div className="mt-3">
                  <div className="small text-muted mb-1">{isEnglish ? 'Underwater drawdown' : '水下回撤曲线'}</div>
                  {portfolioDrawdownChart}
                </div>
              )}
            </Card.Body>
          </Card>
          <Card className="investment-panel">
            <Card.Header>{isEnglish ? 'Per-symbol summary' : '个股摘要'}</Card.Header>
            <Card.Body>
              <Table size="sm" bordered hover>
                <thead>
                  <tr>
                    <th>{isEnglish ? 'Symbol' : '代码'}</th>
                    <th>{isEnglish ? 'Strategy' : '策略'}</th>
                    <th>{isEnglish ? 'B&H' : '持有'}</th>
                    <th>{isEnglish ? 'Weight' : '权重'}</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(portfolioResult.per_symbol || {}).map(([sym, row]) => (
                    <tr key={sym}>
                      <td>{sym}</td>
                      <td>{row.skipped ? '-' : fmtPct(row.strategy_return)}</td>
                      <td>{row.skipped ? '-' : fmtPct(row.buy_hold_return)}</td>
                      <td>{fmtPct(portfolioResult.weights?.[sym])}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        </>
      )}
    </>
  );
};

export default PortfolioPage;
