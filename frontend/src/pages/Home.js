import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Badge, Button, Card, Col, Form, Row, Spinner } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { useAppI18n } from '../i18n';
import PageLogo from '../components/PageLogo';
import stockApiService from '../services/stockApi';
import '../styles/Home.css';

const resolveNewsLink = (item) => {
  const raw = String(item?.url || '').trim();
  if (raw && /^https?:\/\//i.test(raw)) {
    return raw;
  }
  const title = encodeURIComponent(String(item?.title || '').trim());
  return `https://www.bing.com/news/search?q=${title}`;
};

const Home = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const navigate = useNavigate();
  const [keyword, setKeyword] = useState('');
  const [newsLimit, setNewsLimit] = useState(80);
  const [useSina, setUseSina] = useState(true);
  const [useAkshare, setUseAkshare] = useState(true);
  const [newsItems, setNewsItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [updatedAt, setUpdatedAt] = useState('');

  const moduleCards = useMemo(
    () =>
      isEnglish
        ? [
            { title: 'Forecasts', desc: 'Multi-model voting with confidence outputs', path: '/predictions' },
            { title: 'Backtests', desc: 'Benchmark comparison and stability validation', path: '/backtest' },
            { title: 'Sentiment', desc: 'Market-wide news and breadth scoring', path: '/market-sentiment' },
            { title: 'AI Insights', desc: 'Natural language trading explanations', path: '/ai-chat' },
          ]
        : [
            { title: '智能预测', desc: '多模型投票与置信区间输出', path: '/predictions' },
            { title: '回测评估', desc: '策略基线对比与稳健性验证', path: '/backtest' },
            { title: '市场情绪', desc: '全市场新闻舆情融合评分', path: '/market-sentiment' },
            { title: 'AI 研判', desc: '自然语言生成交易解释', path: '/ai-chat' },
          ],
    [isEnglish]
  );

  const sourceText = useMemo(() => {
    const list = [];
    if (useSina) list.push('sina');
    if (useAkshare) list.push('akshare');
    return list.join(',');
  }, [useSina, useAkshare]);

  const fetchNews = useCallback(
    async (force = false) => {
      if (!sourceText) {
        setError(isEnglish ? 'Please select at least one news source.' : '请至少选择一个新闻来源');
        return;
      }
      setLoading(true);
      setError('');
      try {
        const params = new URLSearchParams();
        params.append('limit', String(Math.max(20, Math.min(400, Number(newsLimit) || 80))));
        params.append('sources', sourceText);
        if (keyword.trim()) params.append('keyword', keyword.trim());
        if (force) stockApiService.clearCache('/api/news/realtime');
        const resp = await stockApiService.request(`/api/news/realtime?${params.toString()}`, {
          method: 'GET',
        });
        if (!resp?.success) {
          throw new Error(resp?.message || (isEnglish ? 'Failed to load financial news.' : '加载财经新闻失败'));
        }
        setNewsItems(Array.isArray(resp?.data?.items) ? resp.data.items : []);
        setUpdatedAt(new Date().toLocaleTimeString());
      } catch (e) {
        setNewsItems([]);
        setError(e?.message || (isEnglish ? 'Failed to load financial news.' : '加载财经新闻失败'));
      } finally {
        setLoading(false);
      }
    },
    [isEnglish, keyword, newsLimit, sourceText]
  );

  useEffect(() => {
    fetchNews(false);
  }, [fetchNews]);

  return (
    <div className="analysis-page home-page">
      <section className="home-hero mb-3">
        <div className="home-hero-main">
          <PageLogo title="AlphaScope Live" subtitle="Market Intelligence" glyph="S" tone="orange" />
          <Badge bg="light" text="dark">
            Quant x AI
          </Badge>
          <h1>{isEnglish ? 'AlphaScope Intelligent Research Cockpit' : 'AlphaScope 智能投研驾驶舱'}</h1>
          <p>
            {isEnglish
              ? 'Built for pre-trade decisions by combining live financial news, quantitative forecasts, backtests, and sentiment analysis into one explainable workflow.'
              : '面向交易前决策场景，融合实时财经新闻、量化预测、回测验证与市场情绪分析。你看到的不只是信号，而是可解释、可验证、可执行的结论链路。'}
          </p>
          <div className="home-hero-actions">
            <Button onClick={() => navigate('/dashboard')}>
              {isEnglish ? 'Open Market Overview' : '进入市场总览'}
            </Button>
            <Button variant="outline-primary" onClick={() => navigate('/predictions')}>
              {isEnglish ? 'Start Forecasting' : '开始智能预测'}
            </Button>
          </div>
        </div>
        <div className="home-hero-side">
          <div className="hero-stat">
            <span>{isEnglish ? 'News Samples' : '新闻样本'}</span>
            <strong>{newsItems.length}</strong>
          </div>
          <div className="hero-stat">
            <span>{isEnglish ? 'Data Sources' : '数据来源'}</span>
            <strong>{sourceText || '-'}</strong>
          </div>
          <div className="hero-stat">
            <span>{isEnglish ? 'Last Refresh' : '最近刷新'}</span>
            <strong>{updatedAt || '--:--:--'}</strong>
          </div>
        </div>
      </section>

      <Row className="g-3 mb-3">
        {moduleCards.map((item) => (
          <Col md={6} xl={3} key={item.title}>
            <Card className="module-card h-100" role="button" onClick={() => navigate(item.path)}>
              <Card.Body>
                <div className="module-title">{item.title}</div>
                <div className="module-desc">{item.desc}</div>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>

      <Card className="mb-3">
        <Card.Body>
          <Row className="g-3 align-items-end">
            <Col md={4}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'Keyword Focus' : '定向关键词'}</Form.Label>
                <Form.Control
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  placeholder={isEnglish ? 'For example: AI, chips, rate cut' : '例如：AI、半导体、降息'}
                />
              </Form.Group>
            </Col>
            <Col md={2}>
              <Form.Group>
                <Form.Label>{isEnglish ? 'News Limit' : '抓取条数'}</Form.Label>
                <Form.Control
                  type="number"
                  min={20}
                  max={400}
                  value={newsLimit}
                  onChange={(e) => setNewsLimit(Number(e.target.value || 80))}
                />
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Label>{isEnglish ? 'Sources' : '来源'}</Form.Label>
              <div className="d-flex gap-3">
                <Form.Check type="checkbox" label="Sina" checked={useSina} onChange={(e) => setUseSina(e.target.checked)} />
                <Form.Check type="checkbox" label="AKShare" checked={useAkshare} onChange={(e) => setUseAkshare(e.target.checked)} />
              </div>
            </Col>
            <Col md={3}>
              <Button onClick={() => fetchNews(true)} disabled={loading}>
                {loading ? (
                  <>
                    <Spinner animation="border" size="sm" className="me-2" />
                    {isEnglish ? 'Fetching...' : '抓取中...'}
                  </>
                ) : (
                  isEnglish ? 'Refresh News' : '刷新新闻'
                )}
              </Button>
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {error && <Card className="mb-3 p-3 text-danger">{error}</Card>}

      <Card>
        <Card.Header className="d-flex justify-content-between align-items-center">
          <span>{isEnglish ? 'Realtime Financial News Feed' : '实时财经新闻流'}</span>
          <Badge bg="light" text="dark">
            {isEnglish ? 'Latest Update ' : '最新更新 '}
            {updatedAt || '--:--:--'}
          </Badge>
        </Card.Header>
        <Card.Body>
          {loading && newsItems.length === 0 ? (
            <div className="py-4 text-center">
              <Spinner animation="border" />
            </div>
          ) : newsItems.length === 0 ? (
            <div className="text-muted">
              {isEnglish ? 'No news data is currently available to display.' : '当前没有可展示的新闻数据'}
            </div>
          ) : (
            <div className="home-news-list">
              {newsItems.map((item, idx) => (
                <article className="home-news-item" key={`${item.title}-${idx}`}>
                  <div className="home-news-title">
                    <a href={resolveNewsLink(item)} target="_blank" rel="noreferrer">
                      {item.title}
                    </a>
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
    </div>
  );
};

export default Home;
