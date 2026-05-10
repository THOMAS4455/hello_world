import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, Badge, Button, Card, Col, Container, Form, InputGroup, Pagination, Row, Spinner } from 'react-bootstrap';
import { useAppI18n } from '../i18n';
import PageLogo from '../components/PageLogo';
import '../styles/Dashboard.css';

const PAGE_SIZE = 50;
const FETCH_LIMIT = 1200;

const Dashboard = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const navigate = useNavigate();
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdate, setLastUpdate] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [totalStocks, setTotalStocks] = useState(0);
  const [marketOverview, setMarketOverview] = useState(null);
  const [page, setPage] = useState(1);
  const [remoteSearchStocks, setRemoteSearchStocks] = useState([]);
  const [searchingRemote, setSearchingRemote] = useState(false);
  const [trendFilter, setTrendFilter] = useState('all');
  const [sortKey, setSortKey] = useState('change_desc');

  const fetchStocks = async () => {
    try {
      setLoading(true);
      setError('');
      const stamp = Date.now();
      const [stocksResp, overviewResp] = await Promise.all([
        fetch(`http://localhost:8000/api/stocks?limit=${FETCH_LIMIT}&refresh=1&_=${stamp}`),
        fetch(`http://localhost:8000/api/stocks/market-overview?refresh=1&_=${stamp}`),
      ]);
      const payload = await stocksResp.json();
      const overviewPayload = await overviewResp.json();

      if (payload?.success && Array.isArray(payload?.data?.stocks)) {
        const validStocks = payload.data.stocks.filter(
          (stock) =>
            stock &&
            typeof stock.symbol === 'string' &&
            typeof stock.name === 'string' &&
            Number.isFinite(Number(stock.price))
        );
        setStocks(validStocks);
        setTotalStocks(Number(payload?.data?.total || validStocks.length));
        setMarketOverview(overviewPayload?.success && overviewPayload?.data ? overviewPayload.data : null);
        setLastUpdate(new Date());
        setPage(1);
        return;
      }

      setStocks([]);
      setTotalStocks(0);
      setMarketOverview(null);
      setError(payload?.message || (isEnglish ? 'Unexpected data format.' : '数据格式异常'));
    } catch (err) {
      setStocks([]);
      setTotalStocks(0);
      setMarketOverview(null);
      setError(err?.message || (isEnglish ? 'Failed to fetch stock data.' : '获取股票数据失败'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStocks();
    const timer = setInterval(fetchStocks, 120000);
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
        const resp = await fetch(`http://localhost:8000/api/stocks/search?q=${encodeURIComponent(keyword)}`);
        const payload = await resp.json();
        setRemoteSearchStocks(payload?.success && Array.isArray(payload?.data?.stocks) ? payload.data.stocks : []);
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
    const trendFiltered = sourceStocks.filter((s) => {
      const cp = Number(s.change_percent || 0);
      if (trendFilter === 'up') return cp > 0;
      if (trendFilter === 'down') return cp < 0;
      if (trendFilter === 'flat') return cp === 0;
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
    const riseCount = Number(marketOverview?.rising_stocks) || stocks.filter((s) => Number(s.change_percent || 0) > 0).length;
    const dropCount = Number(marketOverview?.falling_stocks) || stocks.filter((s) => Number(s.change_percent || 0) < 0).length;
    const flatCount =
      Number(marketOverview?.flat_stocks) ||
      Math.max(0, (Number(marketOverview?.total_stocks) || stocks.length) - riseCount - dropCount);
    const avgChange = Number.isFinite(Number(marketOverview?.avg_change_percent))
      ? Number(marketOverview?.avg_change_percent)
      : stocks.length === 0
      ? 0
      : stocks.reduce((acc, s) => acc + Number(s.change_percent || 0), 0) / stocks.length;

    return {
      totalMarket: Number(marketOverview?.total_stocks) || totalStocks || stocks.length,
      riseCount,
      dropCount,
      flatCount,
      avgChange,
    };
  }, [stocks, totalStocks, marketOverview]);

  const formatPrice = (price) =>
    new Intl.NumberFormat(isEnglish ? 'en-US' : 'zh-CN', { style: 'currency', currency: 'CNY' }).format(Number(price || 0));

  const formatPercent = (value = 0) => {
    const num = Number(value || 0);
    return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
  };

  const getChangeClass = (value = 0) => {
    if (value > 0) return 'text-success';
    if (value < 0) return 'text-danger';
    return 'text-muted';
  };

  return (
    <Container className="dashboard-page py-3 py-md-4">
      <div className="dashboard-hero mb-4">
        <div>
          <PageLogo title="Market Console" subtitle="Realtime Watchboard" glyph="D" tone="blue" />
          <div className="hero-tag mb-2">{isEnglish ? 'Realtime Market Cockpit' : '实时市场驾驶舱'}</div>
          <h1 className="mb-2">{isEnglish ? 'Market Overview' : '市场总览'}</h1>
          <p className="mb-0 text-secondary">
            {isEnglish
              ? 'Search, filter, sort, and jump into details from one screen to keep your analysis loop tight.'
              : '一页完成检索、趋势筛选、排序和快捷跳转，分析路径更短，交互更直接。'}
          </p>
        </div>
        <div className="dashboard-hero-actions">
          <Button variant="outline-primary" onClick={fetchStocks} disabled={loading}>
            {loading ? (isEnglish ? 'Refreshing...' : '刷新中...') : isEnglish ? 'Refresh Data' : '刷新数据'}
          </Button>
          <Button variant="primary" onClick={() => navigate('/market-sentiment')}>
            {isEnglish ? 'Sentiment' : '情绪分析'}
          </Button>
          <Button variant="dark" onClick={() => navigate('/ai-chat')}>
            {isEnglish ? 'AI Assistant' : 'AI 助手'}
          </Button>
        </div>
      </div>

      <Row className="g-3 mb-3">
        <Col md={3} sm={6}><Card className="metric-card"><Card.Body><div className="metric-label">{isEnglish ? 'Total Market' : '市场总数'}</div><div className="metric-value">{metrics.totalMarket}</div></Card.Body></Card></Col>
        <Col md={3} sm={6}><Card className="metric-card"><Card.Body><div className="metric-label">{isEnglish ? 'Rising Stocks' : '上涨家数'}</div><div className="metric-value text-success">{metrics.riseCount}</div></Card.Body></Card></Col>
        <Col md={3} sm={6}><Card className="metric-card"><Card.Body><div className="metric-label">{isEnglish ? 'Falling Stocks' : '下跌家数'}</div><div className="metric-value text-danger">{metrics.dropCount}</div></Card.Body></Card></Col>
        <Col md={3} sm={6}><Card className="metric-card"><Card.Body><div className="metric-label">{isEnglish ? 'Average Change' : '平均涨跌幅'}</div><div className={`metric-value ${getChangeClass(metrics.avgChange)}`}>{formatPercent(metrics.avgChange)}</div></Card.Body></Card></Col>
      </Row>

      <Card className="mb-3 dashboard-control-card">
        <Card.Body>
          <Row className="g-2 align-items-center">
            <Col lg={5}>
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
                {searchingRemote && <InputGroup.Text><Spinner animation="border" size="sm" /></InputGroup.Text>}
              </InputGroup>
            </Col>
            <Col lg={4}>
              <div className="trend-filter-group">
                <Button size="sm" variant={trendFilter === 'all' ? 'primary' : 'outline-primary'} onClick={() => { setTrendFilter('all'); setPage(1); }}>{isEnglish ? 'All' : '全部'}</Button>
                <Button size="sm" variant={trendFilter === 'up' ? 'success' : 'outline-success'} onClick={() => { setTrendFilter('up'); setPage(1); }}>{isEnglish ? 'Up' : '上涨'}</Button>
                <Button size="sm" variant={trendFilter === 'down' ? 'danger' : 'outline-danger'} onClick={() => { setTrendFilter('down'); setPage(1); }}>{isEnglish ? 'Down' : '下跌'}</Button>
                <Button size="sm" variant={trendFilter === 'flat' ? 'secondary' : 'outline-secondary'} onClick={() => { setTrendFilter('flat'); setPage(1); }}>{isEnglish ? 'Flat' : '平盘'}</Button>
              </div>
            </Col>
            <Col lg={3}>
              <Form.Select value={sortKey} onChange={(e) => { setSortKey(e.target.value); setPage(1); }}>
                <option value="change_desc">{isEnglish ? 'Change %: High to Low' : '涨跌幅：从高到低'}</option>
                <option value="change_asc">{isEnglish ? 'Change %: Low to High' : '涨跌幅：从低到高'}</option>
                <option value="volume_desc">{isEnglish ? 'Volume: High to Low' : '成交量：从高到低'}</option>
                <option value="price_desc">{isEnglish ? 'Price: High to Low' : '价格：从高到低'}</option>
                <option value="price_asc">{isEnglish ? 'Price: Low to High' : '价格：从低到高'}</option>
              </Form.Select>
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {loading && (
        <Card className="mb-3">
          <Card.Body className="text-center py-5">
            <Spinner animation="border" />
            <p className="mt-2 mb-0">{isEnglish ? 'Loading stock data...' : '正在加载股票数据...'}</p>
          </Card.Body>
        </Card>
      )}

      {!loading && error && (
        <Alert variant="danger" className="mb-3">
          <Alert.Heading>{isEnglish ? 'Failed to Load Data' : '数据加载失败'}</Alert.Heading>
          <p className="mb-2">{error}</p>
          <Button variant="outline-danger" onClick={fetchStocks}>
            {isEnglish ? 'Reload' : '重新加载'}
          </Button>
        </Alert>
      )}

      {!loading && !error && (
        <Card className="dashboard-table-card">
          <Card.Header className="d-flex justify-content-between align-items-center">
            <strong>{isEnglish ? 'Stock List' : '股票列表'}</strong>
            <div className="d-flex align-items-center gap-2">
              <small className="text-muted">
                {isEnglish ? 'Updated ' : '更新时间 '}
                {lastUpdate ? lastUpdate.toLocaleString() : isEnglish ? 'Not updated' : '未更新'}
              </small>
              <Badge bg="secondary">
                {transformedStocks.length} {isEnglish ? `items (page size ${PAGE_SIZE})` : `条（每页 ${PAGE_SIZE}）`}
              </Badge>
            </div>
          </Card.Header>
          <Card.Body>
            {transformedStocks.length === 0 ? (
              <div className="empty-state">{isEnglish ? 'No matching stocks. Try adjusting filters.' : '没有匹配的股票，请调整筛选条件。'}</div>
            ) : (
              <>
                <div className="table-responsive">
                  <table className="table table-hover align-middle mb-0">
                    <thead>
                      <tr>
                        <th>{isEnglish ? 'Symbol' : '代码'}</th>
                        <th>{isEnglish ? 'Name' : '名称'}</th>
                        <th>{isEnglish ? 'Price' : '现价'}</th>
                        <th>{isEnglish ? 'Change' : '涨跌额'}</th>
                        <th>{isEnglish ? 'Change %' : '涨跌幅'}</th>
                        <th>{isEnglish ? 'Volume' : '成交量'}</th>
                        <th>{isEnglish ? 'Market Cap' : '市值'}</th>
                        <th>{isEnglish ? 'Actions' : '操作'}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pagedStocks.map((stock) => (
                        <tr key={stock.symbol}>
                          <td><Badge bg="light" text="dark">{stock.symbol}</Badge></td>
                          <td className="fw-semibold">{stock.name}</td>
                          <td>{formatPrice(stock.price)}</td>
                          <td className={getChangeClass(Number(stock.change || 0))}>
                            {Number(stock.change || 0) >= 0 ? '+' : ''}
                            {Number(stock.change || 0).toFixed(2)}
                          </td>
                          <td className={getChangeClass(Number(stock.change_percent || 0))}>{formatPercent(stock.change_percent)}</td>
                          <td>{Number(stock.volume || 0).toLocaleString()}</td>
                          <td>{stock.market_cap ? `${(Number(stock.market_cap) / 100000000).toFixed(1)}${isEnglish ? 'B CNY' : '亿'}` : 'N/A'}</td>
                          <td>
                            <div className="table-action-group">
                              <Button variant="outline-primary" size="sm" onClick={() => navigate(`/stock/${stock.symbol}`)}>
                                {isEnglish ? 'Details' : '详情'}
                              </Button>
                              <Button variant="outline-success" size="sm" onClick={() => navigate(`/predictions?stock=${stock.symbol}`)}>
                                {isEnglish ? 'Forecast' : '预测'}
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="d-flex justify-content-end mt-3">
                  <Pagination className="mb-0">
                    <Pagination.First disabled={page <= 1} onClick={() => setPage(1)} />
                    <Pagination.Prev disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))} />
                    <Pagination.Item active>{page}</Pagination.Item>
                    <Pagination.Next disabled={page >= pageCount} onClick={() => setPage((p) => Math.min(pageCount, p + 1))} />
                    <Pagination.Last disabled={page >= pageCount} onClick={() => setPage(pageCount)} />
                  </Pagination>
                </div>
              </>
            )}
          </Card.Body>
        </Card>
      )}
    </Container>
  );
};

export default Dashboard;
