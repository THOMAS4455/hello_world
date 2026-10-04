import React, { useState, useEffect } from 'react';
import { Table, Spinner, Alert, Form, Card } from 'react-bootstrap';
import { useAppI18n } from '../i18n';
import stockApiService from '../services/stockApi';

const StockList = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    const fetchStocks = async () => {
      try {
        setLoading(true);
        const data = await stockApiService.getMarketOverview();
        let stocksArray = [];
        if (data && data.success && data.data && Array.isArray(data.data.stocks)) {
          stocksArray = data.data.stocks;
        } else if (data && data.data && Array.isArray(data.data)) {
          stocksArray = data.data;
        } else if (Array.isArray(data)) {
          stocksArray = data;
        }
        setStocks(stocksArray);
      } catch (err) {
        setError(isEnglish ? 'Failed to load stock data.' : '加载股票数据失败');
        console.error('Stock list error:', err);
        setStocks([]);
      } finally {
        setLoading(false);
      }
    };

    fetchStocks();
  }, [isEnglish]);

  const filteredStocks = stocks.filter((stock) => {
    const matchesSearch =
      stock.symbol?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      stock.name?.toLowerCase().includes(searchTerm.toLowerCase());

    if (filter === 'positive') return matchesSearch && (stock.change_percent || 0) > 0;
    if (filter === 'negative') return matchesSearch && (stock.change_percent || 0) < 0;
    return matchesSearch;
  });

  if (loading) {
    return (
      <div className="analysis-page stock-list-page">
        <div className="loading-spinner text-center py-5">
          <Spinner animation="border" role="status">
            <span className="visually-hidden">{isEnglish ? 'Loading...' : '加载中...'}</span>
          </Spinner>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analysis-page stock-list-page">
        <Alert variant="danger">{error}</Alert>
      </div>
    );
  }

  return (
    <div className="analysis-page stock-list-page">
      <h1 className="mb-4">{isEnglish ? 'Stock List' : '股票列表'}</h1>

      <Card className="mb-4">
        <Card.Body>
          <div className="ds-filter-toolbar ds-filter-toolbar--2col">
            <Form.Group className="mb-0">
              <Form.Control
                type="text"
                placeholder={isEnglish ? 'Search stocks...' : '搜索股票...'}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </Form.Group>
            <Form.Select value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="all">{isEnglish ? 'All Stocks' : '全部股票'}</option>
              <option value="positive">{isEnglish ? 'Positive Prediction' : '正向预测'}</option>
              <option value="negative">{isEnglish ? 'Negative Prediction' : '负向预测'}</option>
            </Form.Select>
          </div>
        </Card.Body>
      </Card>

      <Card>
        <Card.Header>
          {isEnglish ? `Stock Analysis (${filteredStocks.length} stocks)` : `股票分析（${filteredStocks.length} 只）`}
        </Card.Header>
        <Card.Body>
          <Table responsive hover>
            <thead>
              <tr>
                <th>{isEnglish ? 'Symbol' : '代码'}</th>
                <th>{isEnglish ? 'Name' : '名称'}</th>
                <th>{isEnglish ? 'Price' : '价格'}</th>
                <th>{isEnglish ? 'Change' : '涨跌'}</th>
                <th>{isEnglish ? 'Turnover' : '换手率'}</th>
                <th>{isEnglish ? 'Prediction' : '预测'}</th>
                <th>{isEnglish ? 'Sentiment' : '情绪'}</th>
                <th>RSI</th>
                <th>{isEnglish ? 'Actions' : '操作'}</th>
              </tr>
            </thead>
            <tbody>
              {filteredStocks.map((stock) => (
                <tr key={stock.symbol}>
                  <td><strong>{stock.symbol || 'N/A'}</strong></td>
                  <td>{stock.name || 'N/A'}</td>
                  <td>¥{(stock.current_price || 0).toFixed(2)}</td>
                  <td className={(stock.change_percent || 0) > 0 ? 'market-up' : (stock.change_percent || 0) < 0 ? 'market-down' : 'market-flat'}>
                    {(stock.change_percent || 0) >= 0 ? '+' : ''}
                    {(stock.change_percent || 0).toFixed(2)}%
                  </td>
                  <td>{(stock.turnover_rate || 0).toFixed(2)}%</td>
                  <td className={stock.prediction > 0.5 ? 'prediction-positive' : 'prediction-negative'}>
                    {stock.prediction ? `${(stock.prediction * 100).toFixed(1)}%` : 'N/A'}
                  </td>
                  <td className={stock.sentiment > 0 ? 'market-up' : stock.sentiment < 0 ? 'market-down' : 'market-flat'}>
                    {stock.sentiment ? stock.sentiment.toFixed(3) : 'N/A'}
                  </td>
                  <td className={stock.rsi > 70 ? 'text-danger' : stock.rsi < 30 ? 'text-success' : ''}>
                    {stock.rsi ? stock.rsi.toFixed(1) : 'N/A'}
                  </td>
                  <td>
                    <button className="btn btn-sm btn-outline-primary me-1">
                      {isEnglish ? 'Details' : '详情'}
                    </button>
                    <button className="btn btn-sm btn-outline-secondary">
                      {isEnglish ? 'Chart' : '图表'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
      </Card>
    </div>
  );
};

export default StockList;
