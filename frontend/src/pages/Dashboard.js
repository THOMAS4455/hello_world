import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Badge,
  Button,
  Card,
  Form,
  InputGroup,
  Pagination,
  Spinner,
} from 'react-bootstrap';
import { useAppI18n } from '../i18n';
import AddToWatchlistButton from '../components/AddToWatchlistButton';
import PageLogo from '../components/PageLogo';
import { useWatchlist } from '../hooks/useWatchlist';
import stockApiService from '../services/stockApi';
import { getMarketChangeClass } from '../utils/stockUtils';
import {
  getMarketAutoRefreshIntervalMs,
  isAshareTradingSession,
  shouldRequestLiveMarketRefresh,
} from '../utils/tradingSession';
import '../styles/Dashboard.css';

const PAGE_SIZE = 50;
const MIN_EXPECTED_STOCKS = 500;

const Dashboard = () => {
  const { language, t } = useAppI18n();
  const isEnglish = language === 'en-US';
  const navigate = useNavigate();
  const watchlistApi = useWatchlist();
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdate, setLastUpdate] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [totalStocks, setTotalStocks] = useState(0);
  const [marketOverview, setMarketOverview] = useState(null);
  const [dataFreshness, setDataFreshness] = useState(null);
  const [dataHealth, setDataHealth] = useState(null);
  const [page, setPage] = useState(1);
  const [remoteSearchStocks, setRemoteSearchStocks] = useState([]);
  const [searchingRemote, setSearchingRemote] = useState(false);
  const [trendFilter, setTrendFilter] = useState('all');
  const [sortKey, setSortKey] = useState('change_desc');

  const fetchStocks = async (forceRefresh = false) => {
    try {
      setLoading(true);
      setError('');
      const refresh = shouldRequestLiveMarketRefresh(forceRefresh);
      const [stocksPayload, overviewResp, healthResp] = await Promise.all([
        stockApiService.getStocksPayload({ refresh }),
        stockApiService.getMarketOverview({ refresh }),
        stockApiService.getDataHealth().catch(() => null),
      ]);

      const stocksResp = stocksPayload?.stocks || [];
      if (Array.isArray(stocksResp)) {
        const validStocks = stocksResp.filter(
          (stock) =>
            stock &&
            typeof stock.symbol === 'string' &&
            typeof stock.name === 'string' &&
            Number.isFinite(Number(stock.price))
        );
        setStocks(validStocks);
        setTotalStocks(Number(stocksPayload?.total || validStocks.length));
        setDataFreshness(stocksPayload?.freshness || null);
        setDataHealth(healthResp || null);
        setMarketOverview(overviewResp || null);
        setLastUpdate(new Date());
        setPage(1);
        return;
      }

      setStocks([]);
      setTotalStocks(0);
      setDataFreshness(null);
      setDataHealth(null);
      setMarketOverview(null);
      setError(t('dashboardUnexpectedFormat'));
    } catch (err) {
      setStocks([]);
      setTotalStocks(0);
      setDataFreshness(null);
      setDataHealth(null);
      setMarketOverview(null);
      setError(err?.message || t('dashboardFetchFailed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStocks(false);
    const intervalMs = getMarketAutoRefreshIntervalMs();
    if (!intervalMs) {
      return undefined;
    }
    const timer = setInterval(() => fetchStocks(false), intervalMs);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const keyword = searchTerm.trim();
    if (!keyword) {
      setRemoteSearchStocks([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setSearchingRemote(true);
        const payload = await stockApiService.searchStocks(keyword);
        setRemoteSearchStocks(Array.isArray(payload) ? payload : []);
      } catch {
        setRemoteSearchStocks([]);
      } finally {
        setSearchingRemote(false);
      }
    }, 280);

    return () => clearTimeout(timer);
  }, [searchTerm]);

  const localFilteredStocks = useMemo(() => {
    const keyword = searchTerm.trim().toLowerCase();
    if (!keyword) return stocks;
    return stocks.filter(
      (stock) => stock.name.toLowerCase().includes(keyword) || stock.symbol.toLowerCase().includes(keyword)
    );
  }, [searchTerm, stocks]);

  const sourceStocks = useMemo(() => {
    const keyword = searchTerm.trim();
    if (!keyword) return localFilteredStocks;
    if (remoteSearchStocks.length > 0) return remoteSearchStocks;
    return localFilteredStocks;
  }, [searchTerm, localFilteredStocks, remoteSearchStocks]);

  const transformedStocks = useMemo(() => {
    const trendFiltered = sourceStocks.filter((stock) => {
      const changePercent = Number(stock.change_percent || 0);
      if (trendFilter === 'up') return changePercent > 0;
      if (trendFilter === 'down') return changePercent < 0;
      if (trendFilter === 'flat') return changePercent === 0;
      return true;
    });

    return [...trendFiltered].sort((a, b) => {
      const ap = Number(a.price || 0);
      const bp = Number(b.price || 0);
      const ac = Number(a.change_percent || 0);
      const bc = Number(b.change_percent || 0);
      const av = Number(a.volume || 0);
      const bv = Number(b.volume || 0);
      if (sortKey === 'change_desc') return bc - ac;
      if (sortKey === 'change_asc') return ac - bc;
      if (sortKey === 'volume_desc') return bv - av;
      if (sortKey === 'price_desc') return bp - ap;
      if (sortKey === 'price_asc') return ap - bp;
      return 0;
    });
  }, [sourceStocks, trendFilter, sortKey]);

  const pagedStocks = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return transformedStocks.slice(start, start + PAGE_SIZE);
  }, [transformedStocks, page]);

  const pageCount = Math.max(1, Math.ceil(transformedStocks.length / PAGE_SIZE));

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

  const metrics = useMemo(() => {
    const riseCount =
      Number(marketOverview?.rising_stocks) ||
      stocks.filter((stock) => Number(stock.change_percent || 0) > 0).length;
    const dropCount =
      Number(marketOverview?.falling_stocks) ||
      stocks.filter((stock) => Number(stock.change_percent || 0) < 0).length;
    const flatCount =
      Number(marketOverview?.flat_stocks) ||
      Math.max(0, (Number(marketOverview?.total_stocks) || stocks.length) - riseCount - dropCount);
    const avgChange = Number.isFinite(Number(marketOverview?.avg_change_percent))
      ? Number(marketOverview?.avg_change_percent)
      : stocks.length === 0
      ? 0
      : stocks.reduce((acc, stock) => acc + Number(stock.change_percent || 0), 0) / stocks.length;

    return {
      totalMarket: Number(marketOverview?.total_stocks) || totalStocks || stocks.length,
      riseCount,
      dropCount,
      flatCount,
      avgChange,
    };
  }, [stocks, totalStocks, marketOverview]);

  const formatPrice = (price) =>
    new Intl.NumberFormat(isEnglish ? 'en-US' : 'zh-CN', {
      style: 'currency',
      currency: 'CNY',
    }).format(Number(price || 0));

  const sourceHealthRows = useMemo(() => {
    const entries = Object.entries(dataHealth?.source_health || {});
    return entries.sort(([a], [b]) => a.localeCompare(b));
  }, [dataHealth]);

  const formatPercent = (value = 0) => {
    const num = Number(value || 0);
    return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
  };

  const getChangeClass = (value = 0) => getMarketChangeClass(value);

  const isPartialMarketData = metrics.totalMarket > 0 && metrics.totalMarket < MIN_EXPECTED_STOCKS;
  const inTradingSession = dataFreshness?.in_trading_session ?? isAshareTradingSession();
  const usingSessionSnapshot = Boolean(dataFreshness?.refresh_skipped || (!dataFreshness?.is_live && !inTradingSession));
  const isLive = !usingSessionSnapshot && !isPartialMarketData && totalStocks > 0;

  return (
    <div className="analysis-page dashboard-page">
      <div className="dashboard-hero mb-4">
        <div>
          <div className="hero-tag mb-2">
            {t('dashboardHeroTag')}
            <span className={`freshness-badge ms-2 ${isLive ? 'live' : 'stale'}`}>
              <span className={`live-indicator ${isLive ? '' : 'stale'}`} />
              {isLive ? (isEnglish ? 'Live' : '实时') : (isEnglish ? 'Snapshot' : '快照')}
            </span>
          </div>
          <h1 className="mb-2">{t('dashboardTitle')}</h1>
          <p className="mb-0">{t('dashboardDescription')}</p>
        </div>
        <div className="dashboard-hero-actions">
          <Button variant="outline-primary" onClick={() => fetchStocks(true)} disabled={loading}>
            {loading ? t('dashboardRefreshing') : t('dashboardRefresh')}
          </Button>
          <Button variant="outline-success" onClick={() => navigate('/investment')}>
            {isEnglish ? 'Portfolio' : '投资组合'}
          </Button>
        </div>
      </div>

      <div className="ds-metrics-grid mb-3">
        <Card className="metric-card hover-card">
          <Card.Body>
            <div className="metric-label">{t('dashboardTotalMarket')}</div>
            <div className="metric-value">{metrics.totalMarket.toLocaleString()}</div>
          </Card.Body>
        </Card>
        <Card className="metric-card hover-card">
          <Card.Body>
            <div className="metric-label">{t('dashboardRising')}</div>
            <div className="metric-value market-up">{metrics.riseCount.toLocaleString()}</div>
          </Card.Body>
        </Card>
        <Card className="metric-card hover-card">
          <Card.Body>
            <div className="metric-label">{t('dashboardFalling')}</div>
            <div className="metric-value market-down">{metrics.dropCount.toLocaleString()}</div>
          </Card.Body>
        </Card>
        <Card className="metric-card hover-card">
          <Card.Body>
            <div className="metric-label">{t('dashboardAvgChange')}</div>
            <div className={`metric-value ${getChangeClass(metrics.avgChange)}`}>{formatPercent(metrics.avgChange)}</div>
          </Card.Body>
        </Card>
      </div>

      {dataHealth && sourceHealthRows.length > 0 && (
        <Card className="mb-3">
          <Card.Header className="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <strong>{t('dashboardDataHealth')}</strong>
            <div className="small text-muted">
              {t('dashboardLiveOnly')}: {dataHealth.live_only ? t('dashboardHealthy') : t('dashboardUnhealthy')}
              {' · '}
              {t('dashboardHealthySources')}: {dataHealth.healthy_sources}/{dataHealth.total_sources}
            </div>
          </Card.Header>
          <Card.Body className="p-0">
            <div className="table-responsive">
              <table className="table table-sm mb-0">
                <thead>
                  <tr>
                    <th>{t('dashboardSourceName')}</th>
                    <th>{t('dashboardSourceStatus')}</th>
                    <th>{t('dashboardSourceLatency')}</th>
                    <th>{t('dashboardSourceItems')}</th>
                    <th>{t('dashboardSourceChecked')}</th>
                  </tr>
                </thead>
                <tbody>
                  {sourceHealthRows.map(([source, item]) => (
                    <tr key={source}>
                      <td>{source}</td>
                      <td>
                        <Badge bg={item?.success ? 'success' : 'danger'}>
                          {item?.success ? t('dashboardHealthy') : t('dashboardUnhealthy')}
                        </Badge>
                      </td>
                      <td>{item?.latency_ms ?? '-'}</td>
                      <td>{item?.item_count ?? '-'}</td>
                      <td className="small text-muted">{item?.last_checked_at || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card.Body>
        </Card>
      )}

      {usingSessionSnapshot && (
        <Alert variant="info" className="mb-3">
          {isEnglish
            ? `Outside trading hours (09:25-15:00). Showing the ${dataFreshness?.effective_trading_date || 'latest'} snapshot. Click refresh to force a live pull.`
            : `当前不在交易时段（09:25-15:00），展示 ${dataFreshness?.effective_trading_date || '最新'} 交易日快照。如需强制拉取实时数据，请点击刷新。`}
        </Alert>
      )}

      {isPartialMarketData && (
        <Alert variant="warning" className="mb-3">
          {isEnglish
            ? `Only ${metrics.totalMarket} stocks were loaded from live sources. Please retry refresh — cached snapshots are no longer used for market data.`
            : `实时源仅拉取到 ${metrics.totalMarket} 只股票。请重试刷新——市场数据已不再使用缓存快照。`}
          {dataFreshness?.source && (
            <div className="small mt-1 text-muted">
              {isEnglish ? 'Source' : '数据源'}: {dataFreshness.source}
              {dataFreshness?.source_summary?.baseline_source
                ? ` / ${isEnglish ? 'baseline' : '基线'}: ${dataFreshness.source_summary.baseline_source}`
                : ''}
            </div>
          )}
        </Alert>
      )}

      <Card className="mb-3 dashboard-control-card">
        <Card.Body>
          <div className="ds-filter-toolbar">
            <InputGroup>
                <InputGroup.Text>{isEnglish ? 'Search' : '搜索'}</InputGroup.Text>
                <Form.Control
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value);
                    setPage(1);
                  }}
                  placeholder={isEnglish ? 'Enter stock name or symbol' : '输入股票名称或代码'}
                  aria-label="stock-search"
                />
                {searchTerm && (
                  <Button
                    variant="outline-secondary"
                    onClick={() => {
                      setSearchTerm('');
                      setRemoteSearchStocks([]);
                      setPage(1);
                    }}
                  >
                    {isEnglish ? 'Clear' : '清空'}
                  </Button>
                )}
                {searchingRemote && (
                  <InputGroup.Text>
                    <Spinner animation="border" size="sm" />
                  </InputGroup.Text>
                )}
              </InputGroup>
            <div className="trend-filter-group">
                <Button size="sm" variant={trendFilter === 'all' ? 'primary' : 'outline-primary'} onClick={() => { setTrendFilter('all'); setPage(1); }}>
                  {isEnglish ? 'All' : '全部'}
                </Button>
                <Button size="sm" variant={trendFilter === 'up' ? 'danger' : 'outline-danger'} onClick={() => { setTrendFilter('up'); setPage(1); }}>
                  {isEnglish ? 'Up' : '上涨'}
                </Button>
                <Button size="sm" variant={trendFilter === 'down' ? 'success' : 'outline-success'} onClick={() => { setTrendFilter('down'); setPage(1); }}>
                  {isEnglish ? 'Down' : '下跌'}
                </Button>
                <Button size="sm" variant={trendFilter === 'flat' ? 'secondary' : 'outline-secondary'} onClick={() => { setTrendFilter('flat'); setPage(1); }}>
                  {isEnglish ? 'Flat' : '平盘'}
                </Button>
            </div>
            <Form.Select value={sortKey} onChange={(e) => { setSortKey(e.target.value); setPage(1); }}>
                <option value="change_desc">{isEnglish ? 'Change %: High to Low' : '涨跌幅：从高到低'}</option>
                <option value="change_asc">{isEnglish ? 'Change %: Low to High' : '涨跌幅：从低到高'}</option>
                <option value="volume_desc">{isEnglish ? 'Volume: High to Low' : '成交量：从高到低'}</option>
                <option value="price_desc">{isEnglish ? 'Price: High to Low' : '价格：从高到低'}</option>
                <option value="price_asc">{isEnglish ? 'Price: Low to High' : '价格：从低到高'}</option>
            </Form.Select>
          </div>
        </Card.Body>
      </Card>

      {loading && (
        <div className="text-center py-5">
          <Spinner animation="border" />
          <p className="mt-2 mb-0">{isEnglish ? 'Loading stock data...' : '正在加载股票数据...'}</p>
        </div>
      )}

      {!loading && error && (
        <Alert variant="danger" className="mb-3">
          <Alert.Heading>{isEnglish ? 'Failed to Load Data' : '数据加载失败'}</Alert.Heading>
          <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <span>{error}</span>
            <Button variant="outline-danger" size="sm" onClick={fetchStocks}>
              {isEnglish ? 'Reload' : '重新加载'}
            </Button>
          </div>
        </Alert>
      )}

      {!loading && !error && (
        <Card className="dashboard-stock-table">
          <Card.Header className="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <strong>{isEnglish ? 'A-Share Market' : 'A股行情'}</strong>
            <div className="d-flex align-items-center gap-2 text-muted small">
              <span>
                {transformedStocks.length.toLocaleString()} / {totalStocks ? totalStocks.toLocaleString() : stocks.length.toLocaleString()}
              </span>
              {lastUpdate && <span className="freshness-badge">{lastUpdate.toLocaleTimeString()}</span>}
            </div>
          </Card.Header>
          <Card.Body className="p-0">
            {transformedStocks.length === 0 ? (
              <div className="empty-state">{isEnglish ? 'No matching stocks. Try adjusting filters.' : '没有匹配的股票，请调整筛选条件。'}</div>
            ) : (
              <div className="table-responsive">
                <table className="table table-hover mb-0">
                  <thead>
                    <tr>
                      <th style={{width: '100px'}}>{isEnglish ? 'Symbol' : '代码'}</th>
                      <th>{isEnglish ? 'Name' : '名称'}</th>
                      <th className="text-end">{isEnglish ? 'Price' : '价格'}</th>
                      <th className="text-end">{isEnglish ? 'Change %' : '涨跌幅'}</th>
                      <th className="text-end d-none d-md-table-cell">{isEnglish ? 'Volume' : '成交量'}</th>
                      <th className="text-end d-none d-lg-table-cell">{isEnglish ? 'Market Cap' : '市值'}</th>
                      <th style={{width: '140px'}}>{isEnglish ? 'Watch' : '关注'}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pagedStocks.map((stock) => {
                      const changeVal = Number(stock.change_percent || 0);
                      const changeDir = changeVal > 0 ? 'up' : changeVal < 0 ? 'down' : 'flat';
                      return (
                      <tr key={stock.symbol} style={{cursor: 'pointer'}} onClick={() => navigate(`/stock/${stock.symbol}`)}>
                        <td><span className="symbol-cell">{stock.symbol}</span></td>
                        <td className="text-muted">{stock.name}</td>
                        <td className="text-end price-cell">{formatPrice(stock.price)}</td>
                        <td className="text-end">
                          <span className={`change-badge ${changeDir}`}>
                            {formatPercent(stock.change_percent)}
                          </span>
                        </td>
                        <td className="text-end num-tabular d-none d-md-table-cell">{Number(stock.volume || 0).toLocaleString()}</td>
                        <td className="text-end num-tabular d-none d-lg-table-cell">{(Number(stock.market_cap || 0) / 1e8).toFixed(1)}亿</td>
                        <td onClick={(e) => e.stopPropagation()}>
                          <div className="d-flex flex-nowrap gap-1">
                            <AddToWatchlistButton
                              symbol={stock.symbol}
                              isEnglish={isEnglish}
                              watchlistApi={watchlistApi}
                            />
                          </div>
                        </td>
                      </tr>
                    )})}
                  </tbody>
                </table>
              </div>
            )}
          </Card.Body>
          {pageCount > 1 && (
            <Card.Footer className="d-flex justify-content-center">
              <Pagination className="mb-0">
                <Pagination.First onClick={() => setPage(1)} disabled={page === 1} />
                <Pagination.Prev onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page === 1} />
                <Pagination.Item active>{page}</Pagination.Item>
                <Pagination.Next onClick={() => setPage((current) => Math.min(pageCount, current + 1))} disabled={page === pageCount} />
                <Pagination.Last onClick={() => setPage(pageCount)} disabled={page === pageCount} />
              </Pagination>
            </Card.Footer>
          )}
        </Card>
      )}
    </div>
  );
};

export default Dashboard;
