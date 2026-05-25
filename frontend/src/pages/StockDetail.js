import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Alert, Badge, Button, Card, Col, Container, Row, Spinner, Table } from 'react-bootstrap';
import Plot from 'react-plotly.js';
import { useAppI18n } from '../i18n';
import PageLogo from '../components/PageLogo';
import stockApiService from '../services/stockApi';
import '../styles/StockDetail.css';

const parseIndicators = (indicators) => {
  if (!indicators || typeof indicators !== 'object') return [];
  return Object.entries(indicators).map(([name, payload]) => ({
    name,
    value: typeof payload?.value === 'number' ? payload.value : null,
    signal: payload?.signal || 'HOLD',
  }));
};

const StockDetail = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const { symbol } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [stockData, setStockData] = useState(null);
  const [history, setHistory] = useState([]);
  const [indicators, setIndicators] = useState([]);

  const fetchDetail = async () => {
    if (!symbol) {
      setError(isEnglish ? 'Missing stock symbol.' : '缺少股票代码。');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError('');
      const detail = await stockApiService.getStockDetail(symbol);
      setStockData(detail);
      setHistory(Array.isArray(detail.history) ? detail.history : []);
      setIndicators(parseIndicators(detail.indicators));
    } catch (err) {
      setError(err?.message || (isEnglish ? 'Failed to load stock details.' : '加载股票详情失败。'));
      setStockData(null);
      setHistory([]);
      setIndicators([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetail();
  }, [symbol]);

  const chartSource = useMemo(() => {
    if (!history.length) return [];
    return [...history].sort((a, b) => String(a.date).localeCompare(String(b.date)));
  }, [history]);

  const price = Number(stockData?.current_price ?? stockData?.price ?? 0);
  const changePercent = Number(stockData?.change_percent ?? 0);
  const changeClass = changePercent >= 0 ? 'text-success' : 'text-danger';

  if (loading) {
    return (
      <Container className="py-5 text-center stock-detail-page">
        <Spinner animation="border" />
        <p className="mt-3 mb-0">{isEnglish ? 'Loading stock details...' : '正在加载股票详情...'}</p>
      </Container>
    );
  }

  if (error || !stockData) {
    return (
      <Container className="py-4 stock-detail-page">
        <Alert variant="danger">{error || (isEnglish ? 'Stock data not found.' : '未找到股票数据。')}</Alert>
        <Button onClick={() => navigate('/')} variant="primary">
          {isEnglish ? 'Back to Home' : '返回首页'}
        </Button>
      </Container>
    );
  }

  return (
    <Container className="py-4 stock-detail-page">
      <Button variant="outline-secondary" className="mb-3" onClick={() => navigate('/')}>
        {isEnglish ? 'Back to Home' : '返回首页'}
      </Button>

      <section className="stock-detail-hero">
        <div>
          <PageLogo
            title={isEnglish ? 'Stock Detail' : '股票详情'}
            subtitle={isEnglish ? 'Price, history, and signals' : '价格、历史与信号'}
            glyph="K"
            tone="blue"
            compact
          />
          <h2>{stockData.name || symbol}</h2>
          <div className="stock-detail-subtext mb-3">{stockData.symbol || symbol}</div>
          <div className={`stock-detail-price ${changeClass}`}>
            {price.toFixed(2)} ({changePercent >= 0 ? '+' : ''}
            {changePercent.toFixed(2)}%)
          </div>
        </div>
        <div className="stock-detail-actions">
          <Button variant="outline-light" onClick={() => navigate(`/predictions?stock=${symbol}`)}>
            {isEnglish ? 'Open Forecast' : '查看预测'}
          </Button>
          <Button variant="primary" onClick={() => navigate(`/ai-chat?stock=${symbol}`)}>
            {isEnglish ? 'AI Analysis' : 'AI 分析'}
          </Button>
        </div>
      </section>

      <Row>
        <Col lg={8} className="mb-3">
          <Card className="mb-3">
            <Card.Header>{isEnglish ? 'Price Trend' : '价格走势'}</Card.Header>
            <Card.Body>
              {chartSource.length === 0 ? (
                <div className="text-muted">
                  {isEnglish ? 'No historical price data available for plotting.' : '暂无可绘制的历史价格数据。'}
                </div>
              ) : (
                <Plot
                  data={[
                    {
                      x: chartSource.map((x) => x.date),
                      y: chartSource.map((x) => Number(x.close ?? 0)),
                      type: 'scatter',
                      mode: 'lines',
                      line: { color: '#3b82f6', width: 2 },
                      name: isEnglish ? 'Close' : '收盘价',
                    },
                  ]}
                  layout={{
                    autosize: true,
                    height: 320,
                    paper_bgcolor: '#ffffff',
                    plot_bgcolor: '#ffffff',
                    margin: { l: 46, r: 20, t: 20, b: 44 },
                    xaxis: { title: isEnglish ? 'Date' : '日期' },
                    yaxis: { title: isEnglish ? 'Price' : '价格' },
                  }}
                  config={{ responsive: true, displaylogo: false }}
                  style={{ width: '100%' }}
                />
              )}
            </Card.Body>
          </Card>

          <Card className="mb-3">
            <Card.Header>{isEnglish ? 'Volume' : '成交量'}</Card.Header>
            <Card.Body>
              {chartSource.length === 0 ? (
                <div className="text-muted">
                  {isEnglish ? 'No volume data available for plotting.' : '暂无可绘制的成交量数据。'}
                </div>
              ) : (
                <Plot
                  data={[
                    {
                      x: chartSource.map((x) => x.date),
                      y: chartSource.map((x) => Number(x.volume ?? 0)),
                      type: 'bar',
                      marker: { color: '#94a3b8' },
                      name: isEnglish ? 'Volume' : '成交量',
                    },
                  ]}
                  layout={{
                    autosize: true,
                    height: 240,
                    paper_bgcolor: '#ffffff',
                    plot_bgcolor: '#ffffff',
                    margin: { l: 46, r: 20, t: 20, b: 44 },
                    xaxis: { title: isEnglish ? 'Date' : '日期' },
                    yaxis: { title: isEnglish ? 'Volume' : '成交量' },
                  }}
                  config={{ responsive: true, displaylogo: false }}
                  style={{ width: '100%' }}
                />
              )}
            </Card.Body>
          </Card>

          <Card>
            <Card.Header>{isEnglish ? 'Historical Data' : '历史数据'}</Card.Header>
            <Card.Body>
              {history.length === 0 ? (
                <div className="text-muted">{isEnglish ? 'No historical data available.' : '暂无历史数据。'}</div>
              ) : (
                <div className="stock-detail-table-wrap">
                  <Table striped hover size="sm" className="mb-0">
                    <thead>
                      <tr>
                        <th>{isEnglish ? 'Date' : '日期'}</th>
                        <th>{isEnglish ? 'Open' : '开盘'}</th>
                        <th>{isEnglish ? 'Close' : '收盘'}</th>
                        <th>{isEnglish ? 'High' : '最高'}</th>
                        <th>{isEnglish ? 'Low' : '最低'}</th>
                        <th>{isEnglish ? 'Volume' : '成交量'}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((item, idx) => (
                        <tr key={`${item.date || 'row'}-${idx}`}>
                          <td>{item.date || '-'}</td>
                          <td>{Number(item.open ?? 0).toFixed(2)}</td>
                          <td>{Number(item.close ?? 0).toFixed(2)}</td>
                          <td>{Number(item.high ?? 0).toFixed(2)}</td>
                          <td>{Number(item.low ?? 0).toFixed(2)}</td>
                          <td>{Number(item.volume ?? 0).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>

        <Col lg={4} className="mb-3">
          <Card>
            <Card.Header>{isEnglish ? 'Technical Indicators' : '技术指标'}</Card.Header>
            <Card.Body>
              {indicators.length === 0 ? (
                <div className="text-muted">{isEnglish ? 'No technical indicators available.' : '暂无技术指标。'}</div>
              ) : (
                indicators.map((item) => (
                  <div key={item.name} className="stock-detail-sidebar-item">
                    <div>
                      <div className="fw-semibold">{item.name}</div>
                      <div className="small text-muted">{item.value === null ? '-' : item.value.toFixed(4)}</div>
                    </div>
                    <Badge
                      bg={
                        item.signal === 'BUY'
                          ? 'success'
                          : item.signal === 'SELL'
                          ? 'danger'
                          : 'secondary'
                      }
                    >
                      {item.signal}
                    </Badge>
                  </div>
                ))
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default StockDetail;
