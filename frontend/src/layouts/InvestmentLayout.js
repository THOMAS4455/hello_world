import React, { useMemo } from 'react';
import { Alert, Spinner } from 'react-bootstrap';
import { Outlet, useLocation } from 'react-router-dom';
import PageLogo from '../components/PageLogo';
import InvestmentSubNav from '../components/investment/InvestmentSubNav';
import { ResearchWorkspaceProvider, useResearchWorkspace } from '../contexts/ResearchWorkspaceContext';
import '../styles/InvestmentHub.css';
import '../styles/PredictionBacktest.css';

const SECTION_LABELS = {
  workbench: { en: 'Workbench', zh: '工作台' },
  portfolio: { en: 'Portfolio', zh: '组合' },
  forecast: { en: 'Forecast', zh: '预测' },
  backtest: { en: 'Backtest', zh: '回测' },
  paper: { en: 'Paper', zh: '模拟盘' },
  screener: { en: 'Daily Picks', zh: '每日选股' },
  insights: { en: 'Insights', zh: '洞察' },
};

const InvestmentLayoutShell = () => {
  const location = useLocation();
  const {
    isEnglish,
    t,
    watchlist,
    watchlistLoading,
    error,
    clearError,
  } = useResearchWorkspace();

  const activeSection = useMemo(() => {
    const segment = location.pathname.split('/').filter(Boolean).pop() || 'portfolio';
    return SECTION_LABELS[segment] || SECTION_LABELS.portfolio;
  }, [location.pathname]);

  if (watchlistLoading) {
    return (
      <div className="investment-hub analysis-page">
        <div className="text-center py-5">
          <Spinner animation="border" />
          <div className="text-muted mt-2">
            {isEnglish ? 'Loading research workspace...' : '正在加载投资研究工作台...'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="investment-hub analysis-page">
      <section className="investment-hub-hero">
        <div className="investment-hub-hero-main">
          <PageLogo
            title={t('investmentHubTitle', isEnglish ? 'Research Hub' : '投资研究')}
            subtitle={t('investmentHubSubtitle', isEnglish ? 'Watchlist · Forecast · Backtest · Paper' : '自选 · 预测 · 回测 · 模拟')}
            glyph="I"
            tone="teal"
          />
          <div className="investment-hub-tag">
            {t('investmentHubTag', isEnglish ? 'Unified research workspace' : '一体化研究工作台')}
          </div>
          <h1>
            {t('investmentHubHeadline', isEnglish ? 'Unified investment research workspace' : '一体化投资研究工作台')}
          </h1>
          <p>
            {isEnglish
              ? 'Watchlist, single-stock forecasts, validation backtests, portfolio simulation, and paper trading — in one flow.'
              : '在同一工作流中完成自选管理、单股预测、回测验证、组合回测与模拟盘推进。'}
          </p>
        </div>
        <div className="investment-hub-hero-side">
          <div className="investment-hero-stat">
            <span>{isEnglish ? 'Watchlist' : '自选数量'}</span>
            <strong>{watchlist.length} / 20</strong>
          </div>
          <div className="investment-hero-stat">
            <span>{isEnglish ? 'Current section' : '当前模块'}</span>
            <strong>{isEnglish ? activeSection.en : activeSection.zh}</strong>
          </div>
        </div>
      </section>

      <div className="investment-disclaimer mb-4">
        {isEnglish
          ? 'Research/education only. Paper trading uses T+1 and simplified limit-up/down rules. Not investment advice.'
          : '仅供研究与教学。模拟盘含 T+1 与简化涨跌停规则，不构成投资建议。'}
      </div>

      {error && (
        <Alert variant="danger" onClose={clearError} dismissible>
          {error}
        </Alert>
      )}

      <InvestmentSubNav />
      <Outlet />
    </div>
  );
};

const InvestmentLayout = () => (
  <ResearchWorkspaceProvider>
    <InvestmentLayoutShell />
  </ResearchWorkspaceProvider>
);

export default InvestmentLayout;
