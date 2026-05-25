import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Badge, Button, Card, Col, Form, Row, Spinner } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { useAppI18n } from '../i18n';
import PageLogo from '../components/PageLogo';
import stockApiService from '../services/stockApi';
import '../styles/Home.css';

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
            { title: 'Forecasts', desc: 'Direction, confidence, and AI reasoning in one view.', path: '/predictions' },
            { title: 'Backtests', desc: 'Validate signal quality against historical windows.', path: '/backtest' },
            { title: 'Sentiment', desc: 'Track headline pressure and market breadth quickly.', path: '/market-sentiment' },
            { title: 'AI Insights', desc: 'Ask for plain-language explanations before a trade.', path: '/ai-chat' },
          ]
        : [
            { title: '智能预测', desc: '在同一视图中查看方向、置信度和 AI 解释。', path: '/predictions' },
            { title: '回测评估', desc: '用历史窗口验证信号质量与策略稳定性。', path: '/backtest' },
            { title: '市场情绪', desc: '快速观察新闻压力与市场广度的变化。', path: '/market-sentiment' },
            { title: 'AI 研判', desc: '下单前先获取自然语言解释和风险提示。', path: '/ai-chat' },
          ],
    [isEnglish]
  );

  const activeSources = useMemo(() => {
    const items = [];
    if (useSina) items.push('sina');
    if (useAkshare) items.push('akshare');
    return items;
  }, [useAkshare, useSina]);

  const sourceText = useMemo(() => activeSources.join(', '), [activeSources]);

  const fetchNews = useCallback(
    async (force = false) => {
      if (activeSources.length === 0) {
        setError(isEnglish ? 'Select at least one news source.' : '请至少选择一个新闻来源。');
        return;
      }

      setLoading(true);
      setError('');

      try {
        const params = new URLSearchParams();
        params.append('limit', String(Math.max(20, Math.min(400, Number(newsLimit) || 80))));
        params.append('sources', activeSources.join(','));
        if (keyword.trim()) params.append('keyword', keyword.trim());
        if (force) stockApiService.clearCache('/api/news/realtime');

        const resp = await stockApiService.request(`/api/news/realtime?${params.toString()}`, {
          method: 'GET',
        });

        if (!resp?.success) {
          throw new Error(resp?.message || (isEnglish ? 'Failed to load financial news.' : '加载财经新闻失败。'));
        }

        const items = Array.isArray(resp?.data?.items) ? resp.data.items : [];
        setNewsItems(items);
        setUpdatedAt(new Date().toLocaleTimeString());
      } catch (err) {
        setNewsItems([]);
        setError(err?.message || (isEnglish ? 'Failed to load financial news.' : '加载财经新闻失败。'));
      } finally {
        setLoading(false);
      }
    },
    [activeSources, isEnglish, keyword, newsLimit]
  );

  useEffect(() => {
    fetchNews(false);
  }, [fetchNews]);

  return (
    <div className="analysis-page home-page">
      <section className="home-hero mb-4">
        <div className="home-hero-main">
          <PageLogo
            title={isEnglish ? 'AlphaScope Live' : 'AlphaScope 实时'}
            subtitle={isEnglish ? 'Market intelligence workspace' : '市场情报工作台'}
            glyph="S"
            tone="blue"
          />
          <Badge>Market Research Desk</Badge>
          <h1>{isEnglish ? 'A focused workspace for pre-trade research.' : '面向交易前研究的专注工作台。'}</h1>
          <p>
            {isEnglish
              ? 'Track realtime financial headlines, move into forecasts and backtests, and keep attention on the decision instead of the interface.'
              : '在一个界面里查看实时财经新闻，进入预测与回测模块，并把注意力放在决策本身，而不是分散的页面装饰上。'}
          </p>
          <div className="home-hero-actions">
            <Button onClick={() => navigate('/dashboard')}>
              {isEnglish ? 'Open Market Overview' : '进入市场总览'}
            </Button>
            <Button variant="outline-primary" onClick={() => navigate('/predictions')}>
              {isEnglish ? 'Run Forecasts' : '进入预测模块'}
            </Button>
            <Button variant="outline-light" onClick={() => navigate('/guide')}>
              {isEnglish ? 'User Guide' : '使用指南'}
            </Button>
          </div>
        </div>

        <div className="home-hero-side">
          <div className="hero-stat">
            <span>{isEnglish ? 'Headline Count' : '新闻条数'}</span>
            <strong>{newsItems.length}</strong>
          </div>
          <div className="hero-stat">
            <span>{isEnglish ? 'Live Sources' : '实时来源'}</span>
            <strong>{sourceText || '-'}</strong>
          </div>
          <div className="hero-stat">
            <span>{isEnglish ? 'Last Refresh' : '最近刷新'}</span>
            <strong>{updatedAt || '--:--:--'}</strong>
          </div>
        </div>
      </section>

      <Row className="g-3 mb-4">
        {moduleCards.map((item) => (
          <Col md={6} xl={3} key={item.title}>
            <Card className="module-card" role="button" onClick={() => navigate(item.path)}>
              <Card.Body>
                <div className="module-title">{item.title}</div>
                <div className="module-desc">{item.desc}</div>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>

      <Card className="home-command-card mb-4">
        <Card.Body>
          <div className="mb-3">
            <h2 className="home-section-title">{isEnglish ? 'News Console' : '新闻控制台'}</h2>
            <p className="home-section-subtitle">
              {isEnglish
                ? 'Prioritize finance headlines with real source links. Sina is enabled by default because it usually returns better article URLs.'
                : '优先抓取带真实来源链接的财经新闻。默认启用新浪，因为它通常能返回更稳定的原文地址。'}
            </p>
          </div>

          <div className="home-filter-grid">
            <Form.Group>
              <Form.Label>{isEnglish ? 'Keyword Focus' : '关键词'}</Form.Label>
              <Form.Control
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder={isEnglish ? 'AI, chips, policy easing...' : 'AI、芯片、政策宽松...'}
              />
            </Form.Group>

            <Form.Group>
              <Form.Label>{isEnglish ? 'News Limit' : '数量上限'}</Form.Label>
              <Form.Control
                type="number"
                min={20}
                max={400}
                value={newsLimit}
                onChange={(e) => setNewsLimit(Number(e.target.value || 80))}
              />
            </Form.Group>

            <div>
              <Form.Label>{isEnglish ? 'Sources' : '来源'}</Form.Label>
              <div className="home-source-group">
                <Form.Check type="checkbox" label="Sina" checked={useSina} onChange={(e) => setUseSina(e.target.checked)} />
                <Form.Check type="checkbox" label="AKShare" checked={useAkshare} onChange={(e) => setUseAkshare(e.target.checked)} />
              </div>
            </div>

            <div className="home-filter-actions">
              <Button onClick={() => fetchNews(true)} disabled={loading}>
                {loading ? (
                  <>
                    <Spinner animation="border" size="sm" className="me-2" />
                    {isEnglish ? 'Refreshing...' : '刷新中...'}
                  </>
                ) : (
                  isEnglish ? 'Refresh Feed' : '刷新新闻流'
                )}
              </Button>
            </div>
          </div>
        </Card.Body>
      </Card>

      {error && <Card className="mb-3 p-3 text-danger">{error}</Card>}

      <Card className="home-feed-card">
        <Card.Body>
          <div className="home-feed-header">
            <div>
              <h2 className="home-section-title">{isEnglish ? 'Realtime Financial Headlines' : '实时财经头条'}</h2>
              <p className="home-section-subtitle">
                {isEnglish
                  ? 'Only real fetched headlines are shown. Items without original URLs are displayed as plain text.'
                  : '这里展示的都是真实抓取结果。没有原文链接的条目会按纯文本显示，不再伪装成可点击新闻。'}
              </p>
            </div>
            <Badge>
              {isEnglish ? 'Updated ' : '更新于 '}
              {updatedAt || '--:--:--'}
            </Badge>
          </div>

          {loading && newsItems.length === 0 ? (
            <div className="py-4 text-center">
              <Spinner animation="border" />
            </div>
          ) : newsItems.length === 0 ? (
            <div className="empty-state">{isEnglish ? 'No news available right now.' : '当前暂无新闻。'}</div>
          ) : (
            <div className="news-feed-list">
              {newsItems.map((item, index) => {
                const href = item?.url || item?.link || '';
                return (
                  <Card className="news-feed-item" key={`${item?.title || 'news'}-${index}`}>
                    <Card.Body>
                      <div className="news-feed-meta">
                        <Badge bg="light" text="dark">{item?.source || (isEnglish ? 'Source' : '来源')}</Badge>
                        <span>{item?.time || item?.published_at || '--'}</span>
                      </div>
                      <div className="news-feed-title">{item?.title || (isEnglish ? 'Untitled news item' : '未命名新闻')}</div>
                      {item?.summary && <div className="news-feed-summary">{item.summary}</div>}
                      {href ? (
                        <Button variant="link" className="px-0" href={href} target="_blank" rel="noreferrer">
                          {isEnglish ? 'Read source' : '查看原文'}
                        </Button>
                      ) : (
                        <div className="text-muted small">{isEnglish ? 'No source URL available.' : '暂无原文链接。'}</div>
                      )}
                    </Card.Body>
                  </Card>
                );
              })}
            </div>
          )}
        </Card.Body>
      </Card>
    </div>
  );
};

export default Home;
