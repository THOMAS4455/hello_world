import React from 'react';
import { Card, Badge, Button, Row, Col } from 'react-bootstrap';
import { ArrowUp, ArrowDown, GraphUp, GraphDown } from 'react-bootstrap-icons';
import { useAppI18n } from '../i18n';

const StockCard = ({ stock, onViewDetail, onAnalyze }) => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const isPositive = stock.change >= 0;
  const changeColor = isPositive ? 'success' : 'danger';
  const TrendIcon = isPositive ? GraphUp : GraphDown;
  const ArrowIcon = isPositive ? ArrowUp : ArrowDown;

  return (
    <Card className="h-100 stock-card hover-shadow">
      <Card.Header className="d-flex justify-content-between align-items-center">
        <div>
          <h6 className="mb-0">{stock.symbol}</h6>
          <small className="text-muted">{stock.name}</small>
        </div>
        <Badge bg={changeColor} className="d-flex align-items-center">
          <ArrowIcon className="me-1" size={12} />
          {isPositive ? '+' : ''}
          {stock.change_percent.toFixed(2)}%
        </Badge>
      </Card.Header>

      <Card.Body>
        <Row className="text-center">
          <Col>
            <h4 className="mb-1">¥{stock.price.toFixed(2)}</h4>
            <small className={`text-${changeColor}`}>
              {isPositive ? '+' : ''}
              {stock.change.toFixed(2)}
            </small>
          </Col>
        </Row>

        <div className="mt-3 d-flex justify-content-between align-items-center">
          <small className="text-muted">
            {isEnglish ? 'Volume: ' : '成交量: '}
            {stock.volume.toLocaleString()}
          </small>
          <TrendIcon className={`text-${changeColor}`} size={20} />
        </div>
      </Card.Body>

      <Card.Footer className="bg-transparent">
        <div className="d-grid gap-2">
          <Button variant="outline-primary" size="sm" onClick={() => onViewDetail(stock.symbol)}>
            {isEnglish ? 'View Details' : '查看详情'}
          </Button>
          <Button variant="outline-info" size="sm" onClick={() => onAnalyze(stock.symbol)}>
            {isEnglish ? 'AI Analysis' : 'AI分析'}
          </Button>
        </div>
      </Card.Footer>
    </Card>
  );
};

export default StockCard;
