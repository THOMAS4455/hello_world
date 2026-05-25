import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Form, ListGroup, ProgressBar, Row, Spinner, Table } from 'react-bootstrap';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAppI18n } from '../i18n';
import DecisionCard from '../components/DecisionCard';
import PageLogo from '../components/PageLogo';
import stockApiService from '../services/stockApi';
import '../styles/MarketSentiment.css';

const scoreToPercent = (score) => Math.max(0, Math.min(100, ((Number(score) || 0) + 1) * 50));

const resolveNewsLink = (item) => {
  const raw = String(item?.url || '').trim();
  if (raw && /^https?:\/\//i.test(raw)) return raw;
  const title = encodeURIComponent(String(item?.title || '').trim());
  return `https://www.bing.com/news/search?q=${title}`;
};

const MarketSentiment = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const navigate = useNavigate();
  const location = useLocation();
  const [symbolInput, setSymbolInput] = useState('');
  const [stockSearch, setStockSearch] = useState('');
  const [searchingStocks, setSearchingStocks] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [keywordInput, setKeywordInput] = useState('');
  const [newsLimit, setNewsLimit] = useState(120);
  const [useSina, setUseSina] = useState(true);
  const [useAkshare, setUseAkshare] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const preselectedSymbol = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return (params.get('symbol') || '').trim();
  }, [location.search]);

  const scoreLabel = (score) => {
    if (score >= 0.35) return isEnglish ? 'Optimistic' : '乐观';
    if (score >= 0.1) return isEnglish ? 'Slightly Bullish' : '偏乐观';
    if (score <= -0.35) return isEnglish ? 'Pessimistic' : '悲观';
    if (score <= -0.1) return isEnglish ? 'Slightly Cautious' : '偏谨慎';
    return isEnglish ? 'Neutral' : '中性';
  };

  const scoreVariant = (score) => {
    if (score >= 0.35) return 'success';
    if (score >= 0.1) return 'info';
    if (score <= -0.35) return 'danger';
    if (score <= -0.1) return 'warning';
    return 'secondary';
  };

  const fetchSentiment = useCallback(
    async (symbol = '', forceRefresh = false) => {
      const sources = [];
      if (useSina) sources.push('sina');
      if (useAkshare) sources.push('akshare');
      if (sources.length === 0) {
        setError(isEnglish ? 'Please select at least one news source.' : '请至少选择一个新闻来源。');
        return;
      }

      setLoading(true);
      setError('');
      try {
        const payload = await stockApiService.getMarketSentiment(symbol || null, {
          forceRefresh,
          newsLimit: Math.max(20, Math.min(400, Number(newsLimit) || 120)),
          keyword: keywordInput.trim(),
          sources,
        });
        setResult(payload);
      } catch (err) {
        setResult(null);
        setError(err?.message || (isEnglish ? 'Failed to load market sentiment.' : '加载市场情绪失败。'));
      } finally {
        setLoading(false);
      }
    },
    [isEnglish, keywordInput, newsLimit, useAkshare, useSina]
  );

  useEffect(() => {
    if (preselectedSymbol) {
      setSymbolInput(preselectedSymbol);
      fetchSentiment(preselectedSymbol, false);
      return;
    }
    fetchSentiment('', false);
  }, [fetchSentiment, preselectedSymbol]);

  useEffect(() => {
    const q = stockSearch.trim();
    if (!q) {
      setSearchResults([]);
      return;
    }

    let cancelled = false;
    const timer = setTimeout(async () => {
      setSearchingStocks(true);
      try {
        const resp = await stockApiService.request(`/api/stocks/search?q=${encodeURIComponent(q)}`, { method: 'GET' });
        if (cancelled) return;
        const list = Array.isArray(resp?.data?.stocks) ? resp.data.stocks.filter((item) => item && item.symbol) : [];
        setSearchResults(list.slice(0, 20));
      } catch {
        if (!cancelled) setSearchResults([]);
      } finally {
        if (!cancelled) setSearchingStocks(false);
      }
    }, 260);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [stockSearch]);

  const market = result?.market_metrics || {};
  const news = result?.news_metrics || {};
  const score = Number(result?.score || 0);
  const crawlConfig = result?.crawl_config || {};
  const confidence = Number(result?.confidence || 0);
  const direction = score > 0.1 ? 'bullish' : score < -0.1 ? 'bearish' : 'neutral';
  const quality = confidence >= 0.75 ? 'high' : confidence >= 0.55 ? 'medium' : 'low';

  return (
    <div className="analysis-page sentiment-page">
      <div className="sentiment-header">
        <PageLogo
          title={isEnglish ? 'Sentiment Radar' : '情绪雷达'}
          subtitle={isEnglish ? 'News, breadth, and AI signals' : '新闻、广度与 AI 信号'}
          glyph="M"
          tone="blue"
        />
        <div className="analysis-workspace-tag">{isEnglish ? 'Sentiment Console' : '情绪控制台'}</div>
        <h1>{isEnglish ? 'Market sentiment workspace' : '市场情绪工作台'}</h1>
        <p>
          {isEnglish
            ? 'Blend broad news crawling, keyword filtering, and stock-specific context into an operational sentiment view.'
            : '把大范围新闻抓取、关键词过滤和个股上下文结合起来，形成可执行的情绪工作视图。'}
        </p>
      </div>

      <Card className="mb-3">
        <Card.Body>
          <Row className="g-3 align-items-end">
            <Col md={3}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'Stock Symbol' : '股票代码'}</Form.Label>
                <Form.Control value={symbolInput} onChange={(e) => setSymbolInput(e.target.value)} placeholder={isEnglish ? 'For example: 600519' : '例如：600519'} />
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'Search Stock (symbol / name)' : '搜索股票（代码 / 名称）'}</Form.Label>
                <div className="market-stock-search-wrap">
                  <Form.Control value={stockSearch} onChange={(e) => setStockSearch(e.target.value)} placeholder={isEnglish ? 'Enter keyword to search' : '输入关键词搜索'} />
                  {searchingStocks && <div className="small text-muted mt-1">{isEnglish ? 'Searching...' : '搜索中...'}</div>}
                  {!searchingStocks && searchResults.length > 0 && (
                    <ListGroup className="market-stock-search-list">
                      {searchResults.map((item) => (
                        <ListGroup.Item
                          key={`${item.symbol}-${item.name || ''}`}
                          action
                          onClick={() => {
                            setSymbolInput(String(item.symbol));
                            setStockSearch(`${item.symbol} ${item.name || ''}`.trim());
                            setSearchResults([]);
                          }}
                        >
                          {item.symbol} - {item.name || 'Unknown'}
                        </ListGroup.Item>
                      ))}
                    </ListGroup>
                  )}
                </div>
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'Keyword Filter' : '关键词过滤'}</Form.Label>
                <Form.Control value={keywordInput} onChange={(e) => setKeywordInput(e.target.value)} placeholder={isEnglish ? 'For example: semiconductor' : '例如：半导体'} />
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'News Limit' : '抓取条数'}</Form.Label>
                <Form.Control type="number" min={20} max={400} value={newsLimit} onChange={(e) => setNewsLimit(Number(e.target.value || 120))} />
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Label>{isEnglish ? 'Sources' : '来源'}</Form.Label>
              <div className="d-flex gap-3">
                <Form.Check type="checkbox" label="Sina" checked={useSina} onChange={(e) => setUseSina(e.target.checked)} />
                <Form.Check type="checkbox" label="AKShare" checked={useAkshare} onChange={(e) => setUseAkshare(e.target.checked)} />
              </div>
            </Col>
          </Row>

          <div className="d-flex flex-wrap gap-2 mt-3">
            <Button onClick={() => fetchSentiment(symbolInput.trim(), true)} disabled={loading}>
              {loading ? (
                <>
                  <Spinner as="span" animation="border" size="sm" className="me-2" />
                  {isEnglish ? 'Analyzing...' : '分析中...'}
                </>
              ) : (
                isEnglish ? 'Run Analysis' : '运行分析'
              )}
            </Button>
            <Button variant="outline-secondary" onClick={() => { setSymbolInput(''); fetchSentiment('', true); }} disabled={loading}>
              {isEnglish ? 'Whole Market' : '全市场'}
            </Button>
          </div>
        </Card.Body>
      </Card>

      {error && <Alert variant="danger">{error}</Alert>}

      {result && (
        <>
          <DecisionCard
            title={isEnglish ? 'Unified Sentiment Conclusion' : '统一情绪结论'}
            summary={
              isEnglish
                ? `The current market mood is "${scoreLabel(score)}" with a composite score of ${score.toFixed(4)}. Treat this as a positioning factor and confirm it with strategy evidence before acting.`
                : `当前市场情绪为“${scoreLabel(score)}”，综合分数为 ${score.toFixed(4)}。建议将它作为仓位调整因子，并结合策略证据后再执行。`
            }
            direction={direction}
            confidence={confidence}
            quality={quality}
            riskNote={
              isEnglish
                ? 'Sentiment reacts quickly to event shocks. It works better as a filter or sizing factor than as a standalone trigger.'
                : '情绪对事件冲击反应很快，更适合作为过滤器或仓位因子，而不是单独的入场触发器。'
            }
            evidence={[
              { label: isEnglish ? 'Market Score' : '市场分数', value: score.toFixed(4) },
              { label: isEnglish ? 'News Samples' : '新闻样本', value: String(news.total_news || 0) },
              { label: isEnglish ? 'Rising Stocks' : '上涨家数', value: String(market.rising_count || 0) },
              { label: isEnglish ? 'Falling Stocks' : '下跌家数', value: String(market.falling_count || 0) },
            ]}
          />

          <Row className="g-3 mb-3">
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Composite Score' : '综合情绪分数'}</div><div className="metric-value">{score.toFixed(4)}</div><ProgressBar now={scoreToPercent(score)} variant={scoreVariant(score)} className="mt-2" /></Card.Body></Card></Col>
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Sentiment Label' : '情绪标签'}</div><div className="metric-value"><Badge bg={scoreVariant(score)}>{scoreLabel(score)}</Badge></div><div className="small text-muted mt-2">{isEnglish ? 'Confidence ' : '置信度 '}{(confidence * 100).toFixed(1)}%</div></Card.Body></Card></Col>
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Market Breadth' : '市场广度'}</div><div className="metric-value">{market.rising_count || 0}/{market.total_stocks || 0}</div><div className="small text-muted mt-2">{isEnglish ? 'Rising Ratio ' : '上涨占比 '}{(Number(market.rising_ratio || 0) * 100).toFixed(2)}%</div></Card.Body></Card></Col>
            <Col md={3}><Card className="metric-card h-100"><Card.Body><div className="metric-label">{isEnglish ? 'Crawler Config' : '抓取配置'}</div><div className="metric-value">{crawlConfig.sources?.join(', ') || '-'}</div><div className="small text-muted mt-2">{isEnglish ? 'Limit ' : '条数 '}{crawlConfig.news_limit || 0}</div></Card.Body></Card></Col>
          </Row>

          <Row className="g-3">
            <Col lg={6}>
              <Card className="mb-3">
                <Card.Header>{isEnglish ? 'News Sample' : '新闻样本'}</Card.Header>
                <Card.Body>
                  {(news.news_samples || []).length === 0 ? (
                    <div className="text-muted">{isEnglish ? 'No news samples available.' : '暂无新闻样本。'}</div>
                  ) : (
                    <div className="home-news-list">
                      {news.news_samples.map((item, idx) => (
                        <article className="home-news-item" key={`${item.title}-${idx}`}>
                          <div className="home-news-title">
                            <a href={resolveNewsLink(item)} target="_blank" rel="noreferrer">{item.title}</a>
                          </div>
                          <div className="home-news-meta">
                            <Badge bg="info">{item.source || 'unknown'}</Badge>
                            <span>{item.time || ''}</span>
                          </div>
                        </article>
                      ))}
                    </div>
                  )}
                </Card.Body>
              </Card>
            </Col>
            <Col lg={6}>
              <Card className="mb-3">
                <Card.Header>{isEnglish ? 'Market Breadth Details' : '市场广度明细'}</Card.Header>
                <Card.Body>
                  <Table size="sm" bordered hover>
                    <tbody>
                      <tr><td>{isEnglish ? 'Rising Count' : '上涨家数'}</td><td>{market.rising_count || 0}</td></tr>
                      <tr><td>{isEnglish ? 'Falling Count' : '下跌家数'}</td><td>{market.falling_count || 0}</td></tr>
                      <tr><td>{isEnglish ? 'Flat Count' : '平盘家数'}</td><td>{market.flat_count || 0}</td></tr>
                      <tr><td>{isEnglish ? 'Total Stocks' : '股票总数'}</td><td>{market.total_stocks || 0}</td></tr>
                    </tbody>
                  </Table>
                  <div className="d-flex gap-2">
                    <Button variant="outline-primary" onClick={() => navigate('/dashboard')}>
                      {isEnglish ? 'Open Dashboard' : '打开看板'}
                    </Button>
                    <Button variant="outline-success" onClick={() => navigate('/ai-chat')}>
                      {isEnglish ? 'Ask AI' : '问 AI'}
                    </Button>
                  </div>
                </Card.Body>
              </Card>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
};

export default MarketSentiment;
