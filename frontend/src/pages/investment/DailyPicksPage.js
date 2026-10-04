import React, { useEffect, useState } from 'react';
import { Badge, Button, Card, Spinner } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { useResearchWorkspace } from '../../contexts/ResearchWorkspaceContext';
import stockApiService from '../../services/stockApi';
import { fmtPct, formatDateTime } from './investmentUtils';

const ACTION_VARIANTS = {
  buy: 'success',
  conditional_buy: 'warning',
  observe: 'secondary',
};

const actionLabel = (action, isEnglish) => {
  const map = {
    buy: { en: 'Buy', zh: '买入' },
    conditional_buy: { en: 'Conditional buy', zh: '条件买入' },
    observe: { en: 'Observe', zh: '观望' },
  };
  return map[action] ? (isEnglish ? map[action].en : map[action].zh) : String(action || '');
};

const DailyPicksPage = () => {
  const navigate = useNavigate();
  const { isEnglish, setError, clearError } = useResearchWorkspace();
  const [picks, setPicks] = useState(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);

  const loadLatest = async () => {
    setLoading(true);
    clearError();
    try {
      const data = await stockApiService.getDailyPicks();
      setPicks(data);
    } catch (e) {
      if (e?.status === 404 || /not found|no daily picks/i.test(String(e?.message || ''))) {
        setPicks(null);
      } else {
        setError(e?.message || 'Failed to load daily picks');
      }
    } finally {
      setLoading(false);
    }
  };

  const runScreener = async () => {
    setRunning(true);
    clearError();
    try {
      const data = await stockApiService.runDailyScreener({ topN: 5 });
      setPicks(data);
    } catch (e) {
      setError(e?.message || 'Screener failed');
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    loadLatest();
    // Intentionally runs once on mount. (The previous eslint-disable directive
    // referenced react-hooks/exhaustive-deps, which is not resolvable in this
    // dependency tree and therefore failed the production build outright.)
  }, []);

  const list = picks?.picks || [];

  return (
    <Card className="investment-panel mb-3">
      <Card.Header className="d-flex justify-content-between align-items-center flex-wrap gap-2">
        <span>{isEnglish ? 'Daily picks · Top 5 predicted risers' : '每日选股 · Top 5 预测上涨'}</span>
        <div className="d-flex gap-2">
          <Button size="sm" variant="outline-secondary" onClick={loadLatest} disabled={loading || running}>
            {loading ? (isEnglish ? 'Loading…' : '加载中…') : isEnglish ? 'Refresh' : '刷新'}
          </Button>
          <Button size="sm" variant="primary" onClick={runScreener} disabled={running || loading}>
            {running ? (
              <>
                <Spinner as="span" animation="border" size="sm" className="me-1" />
                {isEnglish ? 'Scanning…' : '扫描中…'}
              </>
            ) : isEnglish ? 'Run screener' : '运行选股'}
          </Button>
        </div>
      </Card.Header>
      <Card.Body>
        {loading ? (
          <div className="text-center py-4">
            <Spinner animation="border" />
          </div>
        ) : !picks || list.length === 0 ? (
          <div className="text-muted">
            {isEnglish
              ? 'No daily picks yet. Click "Run screener" to scan the whole A-share market (may take 1–3 minutes).'
              : '暂无选股结果。点击「运行选股」扫描 A 股全市场（约需 1–3 分钟）。'}
          </div>
        ) : (
          <>
            <div className="text-muted small mb-3">
              {picks.generated_at
                ? `${isEnglish ? 'Generated' : '生成于'} ${formatDateTime(picks.generated_at)}`
                : ''}
              {picks.risk_note ? <div className="mt-1">{picks.risk_note}</div> : null}
            </div>

            <div className="ds-metrics-grid mb-3">
              <div className="investment-metric-card">
                <div className="investment-metric-label">{isEnglish ? 'Universe scanned' : '扫描标的'}</div>
                <div className="investment-metric-value">{picks.universe?.total ?? '-'}</div>
              </div>
              <div className="investment-metric-card">
                <div className="investment-metric-label">{isEnglish ? 'Picked' : '选中'}</div>
                <div className="investment-metric-value">{list.length}</div>
              </div>
            </div>

            {list.map((p, idx) => (
              <Card className="mb-3" key={p.symbol}>
                <Card.Body>
                  <div className="d-flex justify-content-between align-items-start">
                    <div>
                      <strong>{p.symbol}</strong>
                      {p.name ? <span className="text-muted ms-2">{p.name}</span> : null}
                      <Badge bg="light" text="dark" className="ms-2">
                        #{idx + 1}
                      </Badge>
                    </div>
                    <Badge bg={ACTION_VARIANTS[p.action] || 'secondary'}>
                      {actionLabel(p.action, isEnglish)}
                    </Badge>
                  </div>

                  <div className="ds-metrics-grid mt-3">
                    <div className="investment-metric-card">
                      <div className="investment-metric-label">{isEnglish ? 'Entry' : '入场'}</div>
                      <div className="investment-metric-value">{p.entry_price}</div>
                    </div>
                    <div className="investment-metric-card">
                      <div className="investment-metric-label">{isEnglish ? 'Stop loss' : '止损'}</div>
                      <div className="investment-metric-value market-down">{p.stop_loss}</div>
                    </div>
                    <div className="investment-metric-card">
                      <div className="investment-metric-label">{isEnglish ? 'TP1' : '止盈1'}</div>
                      <div className="investment-metric-value">{p.take_profit_1}</div>
                    </div>
                    <div className="investment-metric-card">
                      <div className="investment-metric-label">{isEnglish ? 'TP2' : '止盈2'}</div>
                      <div className="investment-metric-value">{p.take_profit_2}</div>
                    </div>
                    <div className="investment-metric-card">
                      <div className="investment-metric-label">{isEnglish ? 'TP3' : '止盈3'}</div>
                      <div className="investment-metric-value">{p.take_profit_3}</div>
                    </div>
                    <div className="investment-metric-card">
                      <div className="investment-metric-label">R/R</div>
                      <div className="investment-metric-value">{p.risk_reward_ratio}</div>
                    </div>
                    <div className="investment-metric-card">
                      <div className="investment-metric-label">{isEnglish ? 'Position' : '仓位'}</div>
                      <div className="investment-metric-value">{fmtPct(p.position_pct)}</div>
                    </div>
                    <div className="investment-metric-card">
                      <div className="investment-metric-label">{isEnglish ? 'Shares' : '股数'}</div>
                      <div className="investment-metric-value">
                        {p.position_shares} ({p.position_lots} {isEnglish ? 'lots' : '手'})
                      </div>
                    </div>
                    <div className="investment-metric-card">
                      <div className="investment-metric-label">{isEnglish ? 'Confidence' : '置信度'}</div>
                      <div className="investment-metric-value">{fmtPct(p.prediction_confidence)}</div>
                    </div>
                    <div className="investment-metric-card">
                      <div className="investment-metric-label">{isEnglish ? 'Score' : '评分'}</div>
                      <div className="investment-metric-value">{p.rank_score ?? p.factor_score ?? '-'}</div>
                    </div>
                  </div>

                  {(p.reasons || []).length > 0 && (
                    <div className="text-muted small mt-2">{p.reasons.join(' · ')}</div>
                  )}

                  <div className="mt-3">
                    <Button
                      size="sm"
                      variant="link"
                      className="px-0"
                      onClick={() => navigate(`/investment/forecast?stock=${p.symbol}`)}
                    >
                      {isEnglish ? 'Open forecast' : '查看预测'}
                    </Button>
                  </div>
                </Card.Body>
              </Card>
            ))}
          </>
        )}
      </Card.Body>
    </Card>
  );
};

export default DailyPicksPage;
