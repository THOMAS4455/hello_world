import React, { useMemo, useState } from 'react';
import { Alert, Button, ButtonGroup, Card, Spinner } from 'react-bootstrap';
import Plot from 'react-plotly.js';
import { useAppI18n } from '../i18n';

const StockChart = ({ symbol, data, loading, error, onRefresh }) => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const [chartType, setChartType] = useState('line');

  const source = useMemo(() => (Array.isArray(data) && data.length > 0 ? data : []), [data]);
  const x = source.map((item) => item.date || item.time || '');
  const close = source.map((item) => Number(item.close ?? item.price ?? 0));
  const volume = source.map((item) => Number(item.volume ?? 0));

  if (loading) {
    return (
      <Card>
        <Card.Body className="text-center p-4">
          <Spinner animation="border" />
          <p className="mt-2 mb-0">{isEnglish ? 'Loading chart data...' : '正在加载图表数据...'}</p>
        </Card.Body>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <Card.Body>
          <Alert variant="danger" className="mb-3">
            {isEnglish ? 'Failed to load chart data. Please try again later.' : '图表加载失败，请稍后重试。'}
          </Alert>
          <Button variant="outline-danger" onClick={onRefresh}>
            {isEnglish ? 'Retry' : '重试'}
          </Button>
        </Card.Body>
      </Card>
    );
  }

  if (source.length === 0) {
    return (
      <Card>
        <Card.Body className="text-muted">
          {isEnglish ? 'No real data available to plot.' : '暂无可绘制的真实数据。'}
        </Card.Body>
      </Card>
    );
  }

  const priceTrace =
    chartType === 'candlestick'
      ? {
          x,
          open: source.map((item) => Number(item.open ?? item.price ?? 0)),
          high: source.map((item) => Number(item.high ?? item.price ?? 0)),
          low: source.map((item) => Number(item.low ?? item.price ?? 0)),
          close,
          type: 'candlestick',
          name: isEnglish ? 'Price' : '价格',
        }
      : {
          x,
          y: close,
          type: 'scatter',
          mode: 'lines',
          name: isEnglish ? 'Price' : '价格',
          line: { color: '#007bff', width: 2 },
        };

  const volumeTrace = {
    x,
    y: volume,
    type: 'bar',
    name: isEnglish ? 'Volume' : '成交量',
    marker: { color: '#6c757d' },
  };

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <ButtonGroup>
          <Button
            variant={chartType === 'line' ? 'primary' : 'outline-primary'}
            onClick={() => setChartType('line')}
          >
            {isEnglish ? 'Line' : '折线图'}
          </Button>
          <Button
            variant={chartType === 'candlestick' ? 'primary' : 'outline-primary'}
            onClick={() => setChartType('candlestick')}
          >
            {isEnglish ? 'Candlestick' : 'K 线图'}
          </Button>
        </ButtonGroup>
      </div>

      <Card className="mb-3">
        <Card.Body>
          <Plot
            data={[priceTrace]}
            layout={{
              title: `${symbol || (isEnglish ? 'Stock' : '股票')}${isEnglish ? ' Price Trend' : '价格走势'}`,
              xaxis: { title: isEnglish ? 'Time' : '时间' },
              yaxis: { title: isEnglish ? 'Price' : '价格' },
              height: 380,
              margin: { l: 50, r: 30, t: 50, b: 50 },
            }}
            config={{ responsive: true }}
            style={{ width: '100%' }}
          />
        </Card.Body>
      </Card>

      <Card>
        <Card.Body>
          <Plot
            data={[volumeTrace]}
            layout={{
              title: isEnglish ? 'Volume' : '成交量',
              xaxis: { title: isEnglish ? 'Time' : '时间' },
              yaxis: { title: isEnglish ? 'Volume' : '成交量' },
              height: 220,
              margin: { l: 50, r: 30, t: 50, b: 50 },
            }}
            config={{ responsive: true }}
            style={{ width: '100%' }}
          />
        </Card.Body>
      </Card>
    </div>
  );
};

export default StockChart;
