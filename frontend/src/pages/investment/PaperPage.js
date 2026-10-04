import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button, Card, Spinner, Table } from 'react-bootstrap';
import Plot from 'react-plotly.js';
import { usePredictionTasks } from '../../contexts/PredictionTasksContext';
import { useResearchWorkspace } from '../../contexts/ResearchWorkspaceContext';
import stockApiService from '../../services/stockApi';
import { computeDrawdownSeries } from '../../utils/chartUtils';
import { fmtMoney, fmtPct } from './investmentUtils';

const PaperPage = () => {
  const { isEnglish, watchlist, config, setError, clearError } = useResearchWorkspace();
  const { startTask, completeTask, failTask } = usePredictionTasks();

  const [paperAccount, setPaperAccount] = useState(null);
  const [paperLoading, setPaperLoading] = useState(false);
  const [paperAdvancing, setPaperAdvancing] = useState(false);
  const [paperTrades, setPaperTrades] = useState([]);
  const [replayRemaining, setReplayRemaining] = useState(null);
  const [paperMetrics, setPaperMetrics] = useState(null);
  const activeTaskRef = useRef(null);

  const loadPaperAccount = useCallback(async () => {
    try {
      const acct = await stockApiService.getPaperAccount();
      setPaperAccount(acct);
      if (acct) {
        stockApiService.getPaperTrades(30).then(setPaperTrades).catch(() => setPaperTrades([]));
      }
    } catch {
      setPaperAccount(null);
      setPaperTrades([]);
    }
  }, []);

  useEffect(() => {
    loadPaperAccount();
  }, [loadPaperAccount]);

  const createPaperAccount = async () => {
    setPaperLoading(true);
    clearError();

    const taskId = startTask({
      type: 'paper',
      symbol: 'account',
      params: { action: 'create', capital: config.initial_capital || 100000 },
      route: '/investment/paper',
    });
    activeTaskRef.current = taskId;

    try {
      const acct = await stockApiService.createPaperAccount(config.initial_capital || 100000);
      setPaperAccount(acct);
      setPaperTrades([]);
      completeTask(taskId, { account: acct });
    } catch (e) {
      setError(e.message);
      failTask(taskId, e.message);
    } finally {
      setPaperLoading(false);
      if (activeTaskRef.current === taskId) {
        activeTaskRef.current = null;
      }
    }
  };

  const advancePaperDay = async () => {
    setPaperAdvancing(true);
    clearError();

    const taskId = startTask({
      type: 'paper',
      symbol: 'advance',
      params: { action: 'advance', lastDate: paperAccount?.last_date },
      route: '/investment/paper',
    });
    activeTaskRef.current = taskId;

    try {
      const data = await stockApiService.advancePaperDay();
      setPaperAccount(data?.account || paperAccount);
      setReplayRemaining(data?.replay_remaining_days ?? null);
      const [trades, equityData] = await Promise.all([
        stockApiService.getPaperTrades(30),
        stockApiService.getPaperEquityCurve(),
      ]);
      setPaperTrades(trades);
      setPaperMetrics(equityData?.metrics || null);
      completeTask(taskId, { account: data?.account, trades, metrics: equityData?.metrics });
    } catch (e) {
      setError(e.message);
      failTask(taskId, e.message);
    } finally {
      setPaperAdvancing(false);
      if (activeTaskRef.current === taskId) {
        activeTaskRef.current = null;
      }
    }
  };

  const paperChart = useMemo(() => {
    const curve = paperAccount?.equity_curve || [];
    if (curve.length < 2) return null;
    const x =
      paperAccount.equity_dates?.length === curve.length
        ? paperAccount.equity_dates
        : curve.map((_, i) => i + 1);
    return (
      <Plot
        data={[{ x, y: curve, type: 'scatter', mode: 'lines+markers', name: isEnglish ? 'Paper equity' : '模拟权益' }]}
        layout={{ height: 300, margin: { l: 40, r: 20, t: 20, b: 40 } }}
        config={{ responsive: true, displaylogo: false }}
        style={{ width: '100%' }}
        useResizeHandler
      />
    );
  }, [paperAccount, isEnglish]);

  const paperDrawdownChart = useMemo(() => {
    const curve = paperAccount?.equity_curve || [];
    if (curve.length < 2) return null;
    const x =
      paperAccount.equity_dates?.length === curve.length
        ? paperAccount.equity_dates
        : curve.map((_, i) => i + 1);
    const dd = computeDrawdownSeries(curve);
    return (
      <Plot
        data={[{ x, y: dd, type: 'scatter', mode: 'lines', fill: 'tozeroy', name: isEnglish ? 'Drawdown' : '回撤' }]}
        layout={{ height: 220, margin: { l: 40, r: 20, t: 10, b: 40 }, yaxis: { tickformat: '.1%' } }}
        config={{ responsive: true, displaylogo: false }}
        style={{ width: '100%' }}
        useResizeHandler
      />
    );
  }, [paperAccount, isEnglish]);

  return (
    <>
      <Card className="investment-panel mb-3">
        <Card.Header>{isEnglish ? 'Digital twin paper account' : '数字孪生模拟账户'}</Card.Header>
        <Card.Body>
          {!paperAccount ? (
            <div>
              <p className="text-muted">
                {isEnglish
                  ? 'Create a virtual account to simulate following your watchlist signals day by day.'
                  : '创建虚拟账户，按日模拟跟随自选池信号。'}
              </p>
              <Button variant="primary" onClick={createPaperAccount} disabled={paperLoading}>
                {paperLoading ? <Spinner size="sm" className="me-2" /> : null}
                {isEnglish ? 'Create paper account' : '创建模拟账户'}
              </Button>
            </div>
          ) : (
            <>
              <div className="ds-metrics-grid mb-3">
                <div className="investment-metric-card">
                  <div className="investment-metric-label">{isEnglish ? 'Cash' : '现金'}</div>
                  <div className="investment-metric-value">{fmtMoney(paperAccount.cash)}</div>
                </div>
                <div className="investment-metric-card">
                  <div className="investment-metric-label">{isEnglish ? 'Last equity' : '最新权益'}</div>
                  <div className="investment-metric-value">{fmtMoney((paperAccount.equity_curve || []).slice(-1)[0])}</div>
                </div>
                <div className="investment-metric-card">
                  <div className="investment-metric-label">{isEnglish ? 'Sim date' : '模拟日期'}</div>
                  <div className="investment-metric-value investment-metric-value--compact">{paperAccount.last_date || '-'}</div>
                </div>
                <div className="investment-metric-card">
                  <div className="investment-metric-label">{isEnglish ? 'Positions' : '持仓数'}</div>
                  <div className="investment-metric-value">{Object.keys(paperAccount.positions || {}).length}</div>
                </div>
              </div>
              <Button variant="success" className="me-2" onClick={advancePaperDay} disabled={paperAdvancing || watchlist.length === 0}>
                {paperAdvancing ? <Spinner size="sm" className="me-2" /> : null}
                {isEnglish ? 'Advance one day' : '推进一日'}
              </Button>
              <Button variant="outline-secondary" onClick={createPaperAccount} disabled={paperLoading}>
                {isEnglish ? 'Reset account' : '重置账户'}
              </Button>
              {paperMetrics && (
                <div className="ds-metrics-grid ds-metrics-grid--3 mb-3 mt-3">
                  <div className="investment-metric-card">
                    <div className="investment-metric-label">{isEnglish ? 'Sharpe' : '夏普'}</div>
                    <div className="investment-metric-value">{paperMetrics.sharpe_ratio ?? '-'}</div>
                  </div>
                  <div className="investment-metric-card">
                    <div className="investment-metric-label">{isEnglish ? 'Max drawdown' : '最大回撤'}</div>
                    <div className="investment-metric-value">{fmtPct(paperMetrics.max_drawdown)}</div>
                  </div>
                  <div className="investment-metric-card">
                    <div className="investment-metric-label">{isEnglish ? 'Win rate' : '胜率'}</div>
                    <div className="investment-metric-value">{fmtPct(paperMetrics.win_rate)}</div>
                  </div>
                </div>
              )}
              <div className="text-muted small mt-2">
                {paperAccount.constraints_note}
                {replayRemaining != null && (
                  <span className="ms-2">
                    {isEnglish ? `Replay days left: ${replayRemaining}` : `回放剩余 ${replayRemaining} 日`}
                  </span>
                )}
              </div>
              {paperChart && <div className="mt-3">{paperChart}</div>}
              {paperDrawdownChart && (
                <div className="mt-3">
                  <div className="small text-muted mb-1">{isEnglish ? 'Underwater drawdown' : '水下回撤曲线'}</div>
                  {paperDrawdownChart}
                </div>
              )}
            </>
          )}
        </Card.Body>
      </Card>

      {paperAccount && (
        <Card className="investment-panel">
          <Card.Header>{isEnglish ? 'Recent trades' : '近期成交'}</Card.Header>
          <Card.Body>
            {paperTrades.length === 0 ? (
              <div className="text-muted">{isEnglish ? 'No trades yet.' : '暂无成交。'}</div>
            ) : (
              <Table size="sm" bordered hover>
                <thead>
                  <tr>
                    <th>{isEnglish ? 'Date' : '日期'}</th>
                    <th>{isEnglish ? 'Symbol' : '代码'}</th>
                    <th>{isEnglish ? 'Side' : '方向'}</th>
                    <th>{isEnglish ? 'Shares' : '股数'}</th>
                    <th>{isEnglish ? 'Price' : '价格'}</th>
                  </tr>
                </thead>
                <tbody>
                  {[...paperTrades].reverse().map((tr, idx) => (
                    <tr key={`${tr.date}-${tr.symbol}-${idx}`}>
                      <td>{tr.date}</td>
                      <td>{tr.symbol}</td>
                      <td>{tr.side}</td>
                      <td>{tr.shares}</td>
                      <td>{tr.price}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Card.Body>
        </Card>
      )}
    </>
  );
};

export default PaperPage;
