class AIService {
  constructor() {
    this.baseUrl = 'http://localhost:8000';
  }

  async _post(path, body) {
    const resp = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await resp.json();
    if (!resp.ok || data?.success === false) {
      throw new Error(data?.message || `Request failed: ${resp.status}`);
    }
    return data;
  }

  async checkHealth() {
    const resp = await fetch(`${this.baseUrl}/api/system/health`);
    if (!resp.ok) {
      throw new Error(`Health check failed: ${resp.status}`);
    }
    const data = await resp.json();
    return {
      ai_initialized: data?.data?.components?.ai_service?.status === 'online',
      ...data,
    };
  }

  async analyzeSentiment(text) {
    return this._post('/api/ai/analyze', { query: text });
  }

  async predictMarket(currentPrice, technicalIndicators, priceHistory, marketContext, days = 5) {
    const prompt = `请根据以下信息做${days}天市场预测: 当前价格=${currentPrice}, 技术指标=${JSON.stringify(
      technicalIndicators || {}
    )}, 价格历史=${JSON.stringify((priceHistory || []).slice(-30))}, 市场上下文=${marketContext || ''}`;
    return this._post('/api/ai/analyze', { query: prompt });
  }

  async analyzeTechnical(technicalIndicators, currentPrice, priceHistory) {
    const prompt = `请做技术面分析: 当前价格=${currentPrice}, 技术指标=${JSON.stringify(
      technicalIndicators || {}
    )}, 历史价格=${JSON.stringify((priceHistory || []).slice(-30))}`;
    return this._post('/api/ai/analyze', { query: prompt });
  }

  async assessRisk(symbol, currentSituation, marketEnvironment, positionInfo) {
    const prompt = `请评估股票${symbol}风险。当前情况=${currentSituation}; 市场环境=${marketEnvironment}; 持仓信息=${JSON.stringify(
      positionInfo || {}
    )}`;
    return this._post('/api/ai/analyze', { query: prompt });
  }

  async comprehensiveAnalysis(symbol, currentPrice, priceHistory, marketContext) {
    const [sentiment, prediction, technical, risk] = await Promise.all([
      this.analyzeSentiment(`分析${symbol}市场情绪`),
      this.predictMarket(currentPrice, {}, priceHistory, marketContext, 5),
      this.analyzeTechnical({}, currentPrice, priceHistory),
      this.assessRisk(symbol, `当前价${currentPrice}`, marketContext, { symbol, currentPrice }),
    ]);

    return {
      comprehensive: {
        sentiment: this.formatSentimentResult(sentiment),
        prediction: this.formatPredictionResult(prediction),
        technical: this.formatTechnicalResult(technical),
        risk: this.formatRiskResult(risk),
      },
      sentiment: this.formatSentimentResult(sentiment),
      prediction: this.formatPredictionResult(prediction),
      technical: this.formatTechnicalResult(technical),
      risk: this.formatRiskResult(risk),
    };
  }

  formatSentimentResult(result) {
    const text = result?.data?.response || '';
    return {
      sentiment: 0,
      confidence: 0.8,
      impact: 'medium',
      factors: ['AI text analysis'],
      reasoning: text,
    };
  }

  formatPredictionResult(result) {
    const text = result?.data?.response || '';
    return {
      trend: 'hold',
      risk: 'medium',
      advice: text.slice(0, 120),
      predictions: [],
      reasoning: text,
    };
  }

  formatTechnicalResult(result) {
    const text = result?.data?.response || '';
    return {
      signal: 'hold',
      strength: 0.5,
      trend: 'sideways',
      indicators: {},
      support: [],
      resistance: [],
      recommendations: [],
      reasoning: text,
    };
  }

  formatRiskResult(result) {
    const text = result?.data?.response || '';
    return {
      level: 'medium',
      maxLossProb: 0.3,
      riskReward: 1.5,
      factors: [],
      mitigation: [],
      stopLoss: 0,
      positionSize: 'medium',
      reasoning: text,
    };
  }
}

const aiService = new AIService();
export default aiService;
