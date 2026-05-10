/**
 * AI分析面板组件
 * 提供各种AI分析功能的用户界面
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Form,
  Alert,
  Spinner,
  Badge,
  Tabs,
  Tab,
  Accordion,
  Modal,
  ProgressBar
} from 'react-bootstrap';
import aiService from '../services/aiService';

const AIAnalysisPanel = ({ symbol, currentPrice, priceHistory, technicalIndicators }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState({});
  const [activeTab, setActiveTab] = useState('sentiment');
  const [showModal, setShowModal] = useState(false);
  const [selectedResult, setSelectedResult] = useState(null);
  const [aiStatus, setAiStatus] = useState('checking');

  // 检查AI服务状态
  useEffect(() => {
    checkAIStatus();
  }, []);

  const checkAIStatus = async () => {
    try {
      const status = await aiService.checkHealth();
      setAiStatus(status.ai_initialized ? 'ready' : 'not_ready');
    } catch (error) {
      setAiStatus('error');
      console.error('AI status check failed:', error);
    }
  };

  // 情绪分析
  const handleSentimentAnalysis = async () => {
    if (!symbol) {
      setError('Please enter a stock symbol');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const text = `Analyze market sentiment for ${symbol} stock at current price $${currentPrice}. Consider recent market trends, technical indicators, and overall market conditions.`;
      const result = await aiService.analyzeSentiment(text);
      setResults(prev => ({ ...prev, sentiment: aiService.formatSentimentResult(result) }));
    } catch (error) {
      setError(`Sentiment analysis failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 市场预测
  const handleMarketPrediction = async () => {
    if (!symbol || !currentPrice || !priceHistory || priceHistory.length === 0) {
      setError('Missing required data for prediction');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const marketContext = `Current market conditions for ${symbol}: Technical indicators show ${JSON.stringify(technicalIndicators)}. Recent price action suggests ${priceHistory.slice(-5).map(p => `$${p}`).join(', ')}`;
      const result = await aiService.predictMarket(currentPrice, technicalIndicators, priceHistory, marketContext, 5);
      setResults(prev => ({ ...prev, prediction: aiService.formatPredictionResult(result) }));
    } catch (error) {
      setError(`Market prediction failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 技术分析
  const handleTechnicalAnalysis = async () => {
    if (!symbol || !currentPrice || !priceHistory || priceHistory.length === 0) {
      setError('Missing required data for technical analysis');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await aiService.analyzeTechnical(technicalIndicators, currentPrice, priceHistory);
      setResults(prev => ({ ...prev, technical: aiService.formatTechnicalResult(result) }));
    } catch (error) {
      setError(`Technical analysis failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 风险评估
  const handleRiskAssessment = async () => {
    if (!symbol) {
      setError('Please enter a stock symbol');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const currentSituation = `Current price: $${currentPrice}, Recent performance: ${priceHistory.slice(-5).map(p => `$${p}`).join(', ')}`;
      const marketEnvironment = 'Current market volatility and conditions';
      const positionInfo = { current_price: currentPrice, symbol };
      
      const result = await aiService.assessRisk(symbol, currentSituation, marketEnvironment, positionInfo);
      setResults(prev => ({ ...prev, risk: aiService.formatRiskResult(result) }));
    } catch (error) {
      setError(`Risk assessment failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 综合分析
  const handleComprehensiveAnalysis = async () => {
    if (!symbol || !currentPrice || !priceHistory || priceHistory.length === 0) {
      setError('Missing required data for comprehensive analysis');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const marketContext = `Comprehensive analysis for ${symbol} at $${currentPrice} with technical indicators: ${JSON.stringify(technicalIndicators)}`;
      const result = await aiService.comprehensiveAnalysis(symbol, currentPrice, priceHistory, marketContext);
      setResults(result);
      setActiveTab('comprehensive');
    } catch (error) {
      setError(`Comprehensive analysis failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 显示详细结果
  const showDetailedResult = (resultType) => {
    setSelectedResult({ type: resultType, data: results[resultType] });
    setShowModal(true);
  };

  // 获取情绪颜色
  const getSentimentColor = (sentiment) => {
    if (sentiment > 0.3) return 'success';
    if (sentiment < -0.3) return 'danger';
    return 'warning';
  };

  // 获取风险颜色
  const getRiskColor = (level) => {
    switch (level) {
      case 'low': return 'success';
      case 'medium': return 'warning';
      case 'high': return 'danger';
      default: return 'secondary';
    }
  };

  // 获取信号颜色
  const getSignalColor = (signal) => {
    switch (signal) {
      case 'buy': return 'success';
      case 'sell': return 'danger';
      case 'hold': return 'warning';
      default: return 'secondary';
    }
  };

  return (
    <div className="ai-analysis-panel">
      {/* AI状态指示器 */}
      <div className="mb-3">
        <Badge bg={aiStatus === 'ready' ? 'success' : aiStatus === 'error' ? 'danger' : 'warning'}>
          AI Status: {aiStatus === 'ready' ? 'Ready' : aiStatus === 'error' ? 'Error' : 'Checking...'}
        </Badge>
      </div>

      {/* 错误提示 */}
      {error && (
        <Alert variant="danger" dismissible onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* 快速操作按钮 */}
      <Row className="mb-4">
        <Col md={3}>
          <Button
            variant="primary"
            onClick={handleComprehensiveAnalysis}
            disabled={loading || aiStatus !== 'ready'}
            className="w-100"
          >
            {loading ? <Spinner size="sm" /> : '🤖 Comprehensive Analysis'}
          </Button>
        </Col>
        <Col md={3}>
          <Button
            variant="info"
            onClick={handleSentimentAnalysis}
            disabled={loading || aiStatus !== 'ready'}
            className="w-100"
          >
            {loading ? <Spinner size="sm" /> : '📊 Sentiment'}
          </Button>
        </Col>
        <Col md={3}>
          <Button
            variant="success"
            onClick={handleMarketPrediction}
            disabled={loading || aiStatus !== 'ready'}
            className="w-100"
          >
            {loading ? <Spinner size="sm" /> : '🔮 Predict'}
          </Button>
        </Col>
        <Col md={3}>
          <Button
            variant="warning"
            onClick={handleRiskAssessment}
            disabled={loading || aiStatus !== 'ready'}
            className="w-100"
          >
            {loading ? <Spinner size="sm" /> : '⚠️ Risk'}
          </Button>
        </Col>
      </Row>

      {/* 分析结果标签页 */}
      <Tabs activeKey={activeTab} onSelect={(k) => setActiveTab(k)} className="mb-3">
        <Tab eventKey="comprehensive" title="🤖 Comprehensive">
          {results.comprehensive && (
            <Row>
              <Col md={6}>
                <Card className="mb-3">
                  <Card.Header>
                    <h6>📊 Sentiment Analysis</h6>
                  </Card.Header>
                  <Card.Body>
                    <Badge bg={getSentimentColor(results.comprehensive.sentiment.sentiment)}>
                      Sentiment: {results.comprehensive.sentiment.sentiment.toFixed(2)}
                    </Badge>
                    <div className="mt-2">
                      <small>Confidence: {(results.comprehensive.sentiment.confidence * 100).toFixed(1)}%</small>
                    </div>
                    <div className="mt-2">
                      <small>Impact: {results.comprehensive.sentiment.impact}</small>
                    </div>
                    <Button
                      variant="link"
                      size="sm"
                      onClick={() => showDetailedResult('sentiment')}
                    >
                      View Details →
                    </Button>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={6}>
                <Card className="mb-3">
                  <Card.Header>
                    <h6>🔮 Market Prediction</h6>
                  </Card.Header>
                  <Card.Body>
                    <Badge bg={getSignalColor(results.comprehensive.prediction.trend)}>
                      Trend: {results.comprehensive.prediction.trend.toUpperCase()}
                    </Badge>
                    <div className="mt-2">
                      <small>Risk: {results.comprehensive.prediction.risk}</small>
                    </div>
                    <div className="mt-2">
                      <small>Advice: {results.comprehensive.prediction.advice}</small>
                    </div>
                    <Button
                      variant="link"
                      size="sm"
                      onClick={() => showDetailedResult('prediction')}
                    >
                      View Details →
                    </Button>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={6}>
                <Card className="mb-3">
                  <Card.Header>
                    <h6>📈 Technical Analysis</h6>
                  </Card.Header>
                  <Card.Body>
                    <Badge bg={getSignalColor(results.comprehensive.technical.signal)}>
                      Signal: {results.comprehensive.technical.signal.toUpperCase()}
                    </Badge>
                    <div className="mt-2">
                      <small>Strength: {(results.comprehensive.technical.strength * 100).toFixed(1)}%</small>
                    </div>
                    <div className="mt-2">
                      <small>Trend: {results.comprehensive.technical.trend}</small>
                    </div>
                    <Button
                      variant="link"
                      size="sm"
                      onClick={() => showDetailedResult('technical')}
                    >
                      View Details →
                    </Button>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={6}>
                <Card className="mb-3">
                  <Card.Header>
                    <h6>⚠️ Risk Assessment</h6>
                  </Card.Header>
                  <Card.Body>
                    <Badge bg={getRiskColor(results.comprehensive.risk.level)}>
                      Risk: {results.comprehensive.risk.level.toUpperCase()}
                    </Badge>
                    <div className="mt-2">
                      <small>Max Loss Prob: {(results.comprehensive.risk.maxLossProb * 100).toFixed(1)}%</small>
                    </div>
                    <div className="mt-2">
                      <small>Stop Loss: ${results.comprehensive.risk.stopLoss}</small>
                    </div>
                    <Button
                      variant="link"
                      size="sm"
                      onClick={() => showDetailedResult('risk')}
                    >
                      View Details →
                    </Button>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          )}
        </Tab>

        <Tab eventKey="sentiment" title="📊 Sentiment">
          {results.sentiment && (
            <Card>
              <Card.Header>
                <h6>📊 Market Sentiment Analysis</h6>
              </Card.Header>
              <Card.Body>
                <Row>
                  <Col md={4}>
                    <h6>Sentiment Score</h6>
                    <ProgressBar
                      now={(results.sentiment.sentiment + 1) * 50}
                      variant={getSentimentColor(results.sentiment.sentiment)}
                      className="mb-2"
                    />
                    <p className="text-center">{results.sentiment.sentiment.toFixed(2)}</p>
                  </Col>
                  <Col md={4}>
                    <h6>Confidence</h6>
                    <ProgressBar
                      now={results.sentiment.confidence * 100}
                      variant="info"
                      className="mb-2"
                    />
                    <p className="text-center">{(results.sentiment.confidence * 100).toFixed(1)}%</p>
                  </Col>
                  <Col md={4}>
                    <h6>Market Impact</h6>
                    <Badge bg={getRiskColor(results.sentiment.impact)} className="mb-2">
                      {results.sentiment.impact.toUpperCase()}
                    </Badge>
                  </Col>
                </Row>
                <Row className="mt-3">
                  <Col md={12}>
                    <h6>Key Factors</h6>
                    <div>
                      {results.sentiment.factors.map((factor, index) => (
                        <Badge key={index} bg="secondary" className="me-1 mb-1">
                          {factor}
                        </Badge>
                      ))}
                    </div>
                  </Col>
                </Row>
                <Row className="mt-3">
                  <Col md={12}>
                    <h6>AI Reasoning</h6>
                    <p className="text-muted">{results.sentiment.reasoning}</p>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          )}
        </Tab>

        <Tab eventKey="prediction" title="🔮 Prediction">
          {results.prediction && (
            <Card>
              <Card.Header>
                <h6>🔮 Market Prediction</h6>
              </Card.Header>
              <Card.Body>
                <Row>
                  <Col md={6}>
                    <h6>Overall Trend</h6>
                    <Badge bg={getSignalColor(results.prediction.trend)} className="mb-2">
                      {results.prediction.trend.toUpperCase()}
                    </Badge>
                    <p className="text-muted">{results.prediction.advice}</p>
                  </Col>
                  <Col md={6}>
                    <h6>Risk Level</h6>
                    <Badge bg={getRiskColor(results.prediction.risk)} className="mb-2">
                      {results.prediction.risk.toUpperCase()}
                    </Badge>
                  </Col>
                </Row>
                <Row className="mt-3">
                  <Col md={12}>
                    <h6>5-Day Predictions</h6>
                    <div className="table-responsive">
                      <table className="table table-sm">
                        <thead>
                          <tr>
                            <th>Day</th>
                            <th>Predicted Price</th>
                            <th>Confidence</th>
                            <th>Key Factors</th>
                          </tr>
                        </thead>
                        <tbody>
                          {results.prediction.predictions.map((pred, index) => (
                            <tr key={index}>
                              <td>{pred.day}</td>
                              <td>${pred.predicted_price?.toFixed(2) || 'N/A'}</td>
                              <td>
                                <ProgressBar
                                  now={(pred.confidence || 0) * 100}
                                  variant="info"
                                  style={{ height: '20px' }}
                                />
                              </td>
                              <td>
                                {pred.key_factors?.map((factor, i) => (
                                  <Badge key={i} bg="secondary" className="me-1">
                                    {factor}
                                  </Badge>
                                ))}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Col>
                </Row>
                <Row className="mt-3">
                  <Col md={12}>
                    <h6>AI Reasoning</h6>
                    <p className="text-muted">{results.prediction.reasoning}</p>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          )}
        </Tab>

        <Tab eventKey="technical" title="📈 Technical">
          {results.technical && (
            <Card>
              <Card.Header>
                <h6>📈 Technical Analysis</h6>
              </Card.Header>
              <Card.Body>
                <Row>
                  <Col md={4}>
                    <h6>Overall Signal</h6>
                    <Badge bg={getSignalColor(results.technical.signal)} className="mb-2">
                      {results.technical.signal.toUpperCase()}
                    </Badge>
                    <p className="text-muted">Signal Strength: {(results.technical.strength * 100).toFixed(1)}%</p>
                  </Col>
                  <Col md={4}>
                    <h6>Support Levels</h6>
                    <div>
                      {results.technical.support.map((level, index) => (
                        <Badge key={index} bg="success" className="me-1 mb-1">
                          ${level}
                        </Badge>
                      ))}
                    </div>
                  </Col>
                  <Col md={4}>
                    <h6>Resistance Levels</h6>
                    <div>
                      {results.technical.resistance.map((level, index) => (
                        <Badge key={index} bg="danger" className="me-1 mb-1">
                          ${level}
                        </Badge>
                      ))}
                    </div>
                  </Col>
                </Row>
                <Row className="mt-3">
                  <Col md={12}>
                    <h6>Key Indicators</h6>
                    <div className="table-responsive">
                      <table className="table table-sm">
                        <thead>
                          <tr>
                            <th>Indicator</th>
                            <th>Signal</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(results.technical.indicators).map(([indicator, signal]) => (
                            <tr key={indicator}>
                              <td>{indicator.toUpperCase()}</td>
                              <td>
                                <Badge bg={getSignalColor(signal)}>
                                  {signal.toUpperCase()}
                                </Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Col>
                </Row>
                <Row className="mt-3">
                  <Col md={12}>
                    <h6>Recommendations</h6>
                    <div>
                      {results.technical.recommendations.map((rec, index) => (
                        <Badge key={index} bg="info" className="me-1 mb-1">
                          {rec}
                        </Badge>
                      ))}
                    </div>
                  </Col>
                </Row>
                <Row className="mt-3">
                  <Col md={12}>
                    <h6>AI Reasoning</h6>
                    <p className="text-muted">{results.technical.reasoning}</p>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          )}
        </Tab>

        <Tab eventKey="risk" title="⚠️ Risk">
          {results.risk && (
            <Card>
              <Card.Header>
                <h6>⚠️ Risk Assessment</h6>
              </Card.Header>
              <Card.Body>
                <Row>
                  <Col md={4}>
                    <h6>Risk Level</h6>
                    <Badge bg={getRiskColor(results.risk.level)} className="mb-2">
                      {results.risk.level.toUpperCase()}
                    </Badge>
                  </Col>
                  <Col md={4}>
                    <h6>Max Loss Probability</h6>
                    <ProgressBar
                      now={results.risk.maxLossProb * 100}
                      variant="danger"
                      className="mb-2"
                    />
                    <p className="text-center">{(results.risk.maxLossProb * 100).toFixed(1)}%</p>
                  </Col>
                  <Col md={4}>
                    <h6>Risk/Reward Ratio</h6>
                    <p className="text-center">{results.risk.riskReward?.toFixed(2) || 'N/A'}</p>
                  </Col>
                </Row>
                <Row className="mt-3">
                  <Col md={6}>
                    <h6>Risk Factors</h6>
                    <div>
                      {results.risk.factors.map((factor, index) => (
                        <Badge key={index} bg="warning" className="me-1 mb-1">
                          {factor}
                        </Badge>
                      ))}
                    </div>
                  </Col>
                  <Col md={6}>
                    <h6>Risk Mitigation</h6>
                    <div>
                      {results.risk.mitigation.map((measure, index) => (
                        <Badge key={index} bg="info" className="me-1 mb-1">
                          {measure}
                        </Badge>
                      ))}
                    </div>
                  </Col>
                </Row>
                <Row className="mt-3">
                  <Col md={6}>
                    <h6>Suggested Stop Loss</h6>
                    <p className="text-center h4">${results.risk.stopLoss}</p>
                  </Col>
                  <Col md={6}>
                    <h6>Position Size Recommendation</h6>
                    <p className="text-center h4">{results.risk.positionSize}</p>
                  </Col>
                </Row>
                <Row className="mt-3">
                  <Col md={12}>
                    <h6>AI Reasoning</h6>
                    <p className="text-muted">{results.risk.reasoning}</p>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          )}
        </Tab>
      </Tabs>

      {/* 详细结果模态框 */}
      <Modal show={showModal} onHide={() => setShowModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>
            {selectedResult && `Detailed ${selectedResult.type.charAt(0).toUpperCase() + selectedResult.type.slice(1)} Analysis`}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {selectedResult && (
            <pre className="text-muted">
              {JSON.stringify(selectedResult.data, null, 2)}
            </pre>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowModal(false)}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
};

export default AIAnalysisPanel;
