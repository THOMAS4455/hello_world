import React, { useState } from 'react';
import { Badge, Button, Card } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { useResearchWorkspace } from '../../contexts/ResearchWorkspaceContext';
import stockApiService from '../../services/stockApi';
import { getMarketDirectionBadge } from '../../utils/stockUtils';
import { fmtPct } from './investmentUtils';

const InsightsPage = () => {
  const navigate = useNavigate();
  const { isEnglish, setError, clearError } = useResearchWorkspace();

  const [brief, setBrief] = useState(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const [livePerf, setLivePerf] = useState(null);
  const [liveLoading, setLiveLoading] = useState(false);

  const loadLivePerformance = async () => {
    setLiveLoading(true);
    clearError();
    try {
      const data = await stockApiService.getLivePerformance();
      setLivePerf(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLiveLoading(false);
    }
  };

  const loadBrief = async () => {
    setBriefLoading(true);
    clearError();
    try {
      const data = await stockApiService.getDailyBrief();
      setBrief(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setBriefLoading(false);
    }
  };

  return (
    <>
      <Card className="investment-panel mb-3">
        <Card.Header className="d-flex justify-content-between align-items-center">
          <span>{isEnglish ? 'Live validation (edge vs baseline)' : '实盘验证（相对基线 edge）'}</span>
          <Button size="sm" variant="outline-primary" onClick={loadLivePerformance} disabled={liveLoading}>
            {liveLoading ? (isEnglish ? 'Loading...' : '加载中...') : isEnglish ? 'Refresh' : '刷新'}
          </Button>
        </Card.Header>
        <Card.Body>
          {!livePerf ? (
            <div className="text-muted">
              {isEnglish
                ? 'Metrics come from resolved signals. Small samples are reported as insufficient, never as an improvement.'
                : '指标基于已结算信号计算。样本不足时只标注「样本不足」，不给出任何提升结论。'}
            </div>
          ) : (
            <>
              <div className="ds-metrics-grid mb-3">
                <div className="investment-metric-card">
                  <div className="investment-metric-label">{isEnglish ? 'Resolved' : '已结算'}</div>
                  <div className="investment-metric-value">{livePerf.n_resolved}</div>
                </div>
                <div className="investment-metric-card">
                  <div className="investment-metric-label">{isEnglish ? 'Edge vs baseline' : '相对基线 edge'}</div>
                  <div className={'investment-metric-value ' + ((livePerf.edge || 0) >= 0 ? 'market-up' : 'market-down')}>
                    {livePerf.edge == null ? '—' : fmtPct(livePerf.edge)}
                  </div>
                </div>
                <div className="investment-metric-card">
                  <div className="investment-metric-label">{isEnglish ? 'Majority baseline' : '多数类基线'}</div>
                  <div className="investment-metric-value">
                    {livePerf.baseline_accuracy == null ? '—' : fmtPct(livePerf.baseline_accuracy)}
                  </div>
                </div>
                <div className="investment-metric-card">
                  <div className="investment-metric-label">{isEnglish ? 'Sample' : '样本判定'}</div>
                  <div className="investment-metric-value">
                    {livePerf.insufficient_n
                      ? (isEnglish ? 'Insufficient' : '样本不足')
                      : (isEnglish ? 'Adequate' : '充足')}
                  </div>
                </div>
              </div>
              <p className="text-muted small">{livePerf.message}</p>
            </>
          )}
        </Card.Body>
      </Card>

    <Card className="investment-panel mb-3">
      <Card.Header className="d-flex justify-content-between align-items-center">
        <span>{isEnglish ? 'Daily brief' : '每日简报'}</span>
        <Button size="sm" variant="outline-primary" onClick={loadBrief} disabled={briefLoading}>
          {briefLoading ? (isEnglish ? 'Loading...' : '加载中...') : isEnglish ? 'Refresh' : '刷新'}
        </Button>
      </Card.Header>
      <Card.Body>
        {!brief ? (
          <div className="text-muted">
            {isEnglish
              ? 'Click refresh to generate (may take 1–3 min for large watchlists).'
              : '点击刷新生成简报（自选较多时可能需要 1–3 分钟）。'}
          </div>
        ) : (
          <>
            <div className="ds-metrics-grid mb-3">
              <div className="investment-metric-card">
                <div className="investment-metric-label">{isEnglish ? 'Bullish' : '偏多'}</div>
                <div className="investment-metric-value market-up">{brief.bullish_count}</div>
              </div>
              <div className="investment-metric-card">
                <div className="investment-metric-label">{isEnglish ? 'Bearish' : '偏空'}</div>
                <div className="investment-metric-value market-down">{brief.bearish_count}</div>
              </div>
              <div className="investment-metric-card">
                <div className="investment-metric-label">{isEnglish ? 'Low confidence' : '低可信'}</div>
                <div className="investment-metric-value">{(brief.low_confidence_symbols || []).length}</div>
              </div>
              <div className="investment-metric-card">
                <div className="investment-metric-label">{isEnglish ? 'Watchlist' : '自选数'}</div>
                <div className="investment-metric-value">{brief.watchlist_size}</div>
              </div>
            </div>
            <p className="text-muted small">{brief.risk_note}</p>
            <h6 className="mt-3">{isEnglish ? 'Signal snapshots' : '信号快照'}</h6>
            {(brief.snapshots || []).map((item) => (
              <div className="investment-brief-row" key={item.symbol}>
                <div>
                  <strong>{item.symbol}</strong>
                  {item.error ? (
                    <span className="text-danger ms-2">{item.error}</span>
                  ) : (
                    <Badge className={`ms-2 ${getMarketDirectionBadge(item.direction === 'up' ? 'up' : 'down')}`}>
                      {item.direction === 'up' ? (isEnglish ? 'Bullish' : '偏多') : isEnglish ? 'Bearish' : '偏空'}
                    </Badge>
                  )}
                </div>
                <div>
                  {item.confidence != null && (
                    <span className="me-2">
                      {isEnglish ? 'Conf' : '置信'} {fmtPct(item.confidence)}
                    </span>
                  )}
                  {item.meta_score != null && (
                    <span className="me-2">
                      {isEnglish ? 'Meta' : '元评分'} {item.meta_score}
                    </span>
                  )}
                  {item.trade_allowed != null && (
                    <Badge bg={item.trade_allowed ? 'success' : 'secondary'} className="me-2">
                      {item.trade_allowed ? (isEnglish ? 'Trade OK' : '可交易') : isEnglish ? 'Filtered' : '已过滤'}
                    </Badge>
                  )}
                  {item.signal_stats?.samples > 0 && (
                    <span className="me-2 text-muted small">
                      {isEnglish ? 'Hist acc' : '历史准确率'} {fmtPct(item.signal_stats.accuracy)}
                    </span>
                  )}
                  <Button
                    size="sm"
                    variant="link"
                    onClick={() => navigate(`/investment/forecast?stock=${item.symbol}`)}
                  >
                    {isEnglish ? 'Forecast' : '预测'}
                  </Button>
                </div>
              </div>
            ))}
          </>
        )}
      </Card.Body>
    </Card>
    </>
  );
};

export default InsightsPage;
