import { formatChange, formatPrice, formatVolume } from '../utils/stockUtils';
import { isAshareTradingSession } from '../utils/tradingSession';
import {
  apiRequest,
  buildQuery,
  getApiBaseUrl,
  getAuthHeaders,
  normalizeApiError,
} from './apiClient';

class StockApiService {
  constructor() {
    this.baseUrl = getApiBaseUrl();
    this.cache = new Map();
    this.cacheTimeout = 30000;
    this.liveMarketData = true;
  }

  shouldUseClientCache(cacheKey) {
    if (!this.liveMarketData) {
      return true;
    }
    const key = String(cacheKey || '');
    const marketPrefixes = [
      '/api/stocks',
      '/api/stocks/market-overview',
      '/api/stocks/realtime',
      '/api/stocks/search',
    ];
    if (marketPrefixes.some((prefix) => key.includes(prefix)) && !isAshareTradingSession()) {
      return true;
    }
    const livePrefixes = [
      '/api/stocks',
      '/api/stocks/market-overview',
      '/api/stocks/realtime',
      '/api/stocks/search',
    ];
    return !livePrefixes.some((prefix) => key.includes(prefix));
  }

  getCachedData(key) {
    if (!this.shouldUseClientCache(key)) {
      return null;
    }
    const cached = this.cache.get(key);
    if (!cached) {
      return null;
    }

    if (Date.now() - cached.timestamp >= this.cacheTimeout) {
      this.cache.delete(key);
      return null;
    }

    return cached.data;
  }

  setCachedData(key, data) {
    if (!this.shouldUseClientCache(key)) {
      return;
    }
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    });
  }

  getCacheKey(endpoint, params = {}) {
    return `${endpoint}:${JSON.stringify(params)}`;
  }

  clearCache(pattern = null) {
    if (!pattern) {
      this.cache.clear();
      return;
    }

    for (const key of this.cache.keys()) {
      if (key.includes(pattern)) {
        this.cache.delete(key);
      }
    }
  }

  buildQuery(params = {}) {
    return buildQuery(params);
  }

  getAuthHeaders() {
    return getAuthHeaders();
  }

  normalizeError(status, payload, fallback = 'Request failed') {
    return normalizeApiError(status, payload, fallback);
  }

  normalizeStock(stock = {}) {
    return {
      ...stock,
      formattedPrice: formatPrice(stock.price ?? stock.current_price),
      formattedChange: formatChange(stock.change, stock.change_percent),
      formattedVolume: formatVolume(stock.volume),
    };
  }

  async request(endpoint, options = {}) {
    return apiRequest(endpoint, { ...options, baseUrl: this.baseUrl });
  }

  async getStocksPayload(params = {}) {
    const effectiveParams = {
      limit: 0,
      refresh: false,
      ...params,
    };
    const cacheKey = this.getCacheKey('/api/stocks:payload', effectiveParams);
    const cached = this.getCachedData(cacheKey);
    if (cached) {
      return cached;
    }

    const response = await this.request('/api/stocks', {
      method: 'GET',
      params: effectiveParams,
    });
    const stocks = Array.isArray(response?.data?.stocks) ? response.data.stocks : [];
    const payload = {
      stocks: stocks.map((stock) => this.normalizeStock(stock)),
      total: Number(response?.data?.total || stocks.length),
      returned: Number(response?.data?.returned || stocks.length),
      lastUpdate: response?.data?.last_update || null,
      freshness: response?.data?.freshness || null,
    };
    this.setCachedData(cacheKey, payload);
    return payload;
  }

  async getStocks(params = {}) {
    const payload = await this.getStocksPayload(params);
    return payload.stocks;
  }

  async getMarketOverview(params = {}) {
    const effectiveParams = { refresh: false, ...params };
    const cacheKey = this.getCacheKey('/api/stocks/market-overview', effectiveParams);
    const cached = this.getCachedData(cacheKey);
    if (cached) {
      return cached;
    }

    const response = await this.request('/api/stocks/market-overview', {
      method: 'GET',
      params: effectiveParams,
    });
    this.setCachedData(cacheKey, response.data || null);
    return response.data || null;
  }

  async getStockDetail(symbol, options = {}) {
    if (!symbol) {
      throw new Error('Stock symbol is required');
    }

    const cacheKey = this.getCacheKey(`/api/stocks/${symbol}`, options);
    const cached = this.getCachedData(cacheKey);
    if (cached) {
      return cached;
    }

    const response = await this.request(`/api/stocks/${symbol}`, {
      method: 'GET',
      params: options,
    });
    const detail = response?.data || {};
    const formatted = this.normalizeStock(detail);
    this.setCachedData(cacheKey, formatted);
    return formatted;
  }

  async getStockHistory(symbol, options = {}) {
    const detail = await this.getStockDetail(symbol, options);
    return Array.isArray(detail.history) ? detail.history : [];
  }

  async searchStocks(query) {
    const keyword = String(query || '').trim();
    if (!keyword) {
      return [];
    }

    const cacheKey = this.getCacheKey('/api/stocks/search', { q: keyword });
    const cached = this.getCachedData(cacheKey);
    if (cached) {
      return cached;
    }

    const response = await this.request('/api/stocks/search', {
      method: 'GET',
      params: { q: keyword, refresh: false },
    });
    const stocks = Array.isArray(response?.data?.stocks) ? response.data.stocks : [];
    const formattedStocks = stocks.map((stock) => this.normalizeStock(stock));
    this.setCachedData(cacheKey, formattedStocks);
    return formattedStocks;
  }

  async getRealTimeStocks() {
    const cacheKey = this.getCacheKey('/api/stocks/realtime');
    const cached = this.getCachedData(cacheKey);
    if (cached) {
      return cached;
    }

    const response = await this.request('/api/stocks/realtime', {
      method: 'GET',
    });
    const stocks = Array.isArray(response?.data?.stocks) ? response.data.stocks : [];
    const formattedStocks = stocks.map((stock) => this.normalizeStock(stock));
    this.setCachedData(cacheKey, formattedStocks);
    return formattedStocks;
  }

  async getStockPrediction(symbol, options = {}) {
    if (!symbol) {
      throw new Error('Stock symbol is required');
    }

    const body = {
      symbol,
      horizon: options.horizon ?? 5,
      up_threshold: options.upThreshold ?? options.up_threshold ?? 0.02,
    };
    const controller = new AbortController();
    const timeoutMs = Number(options.timeoutMs || 190000);
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const params = {};
      if (options.taskId) params.task_id = options.taskId;
      const response = await this.request('/api/predictions/predict', {
        method: 'POST',
        params,
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      return response.data;
    } catch (error) {
      if (error?.name === 'AbortError') {
        throw new Error('Prediction request timed out. First run may take up to 3 minutes.');
      }
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }

  async getPredictionHistory(symbol = '', limit = 12) {
    const response = await this.request('/api/predictions/history', {
      method: 'GET',
      params: {
        symbol: symbol || undefined,
        limit,
      },
    });
    return Array.isArray(response?.data?.items) ? response.data.items : [];
  }

  async getPredictionRun(runId) {
    if (!runId) {
      throw new Error('Prediction run id is required');
    }
    const response = await this.request(`/api/predictions/history/${runId}`, {
      method: 'GET',
    });
    return response?.data?.item || null;
  }

  async runBacktest(symbol, options = {}) {
    if (!symbol) {
      throw new Error('Stock symbol is required');
    }

    const body = {
      symbol,
      strategy: options.strategy ?? 'default',
      horizon: options.horizon ?? 5,
      test_size: options.testSize ?? options.test_size ?? 0.2,
      up_threshold: options.upThreshold ?? options.up_threshold ?? 0.02,
      min_confidence: options.minConfidence ?? options.min_confidence ?? 0,
    };
    const params = {};
    if (options.taskId) params.task_id = options.taskId;
    const response = await this.request('/api/predictions/backtest', {
      method: 'POST',
      params,
      body: JSON.stringify(body),
    });
    return response.data;
  }

  async getDataHealth() {
    const response = await this.request('/api/stocks/data-health', {
      method: 'GET',
    });
    return response.data || null;
  }

  async getBacktestHistory(symbol = '', limit = 12) {
    const response = await this.request('/api/predictions/backtest-history', {
      method: 'GET',
      params: {
        symbol: symbol || undefined,
        limit,
      },
    });
    return Array.isArray(response?.data?.items) ? response.data.items : [];
  }

  async getBacktestRun(runId) {
    if (!runId) {
      throw new Error('Backtest run id is required');
    }
    const response = await this.request(`/api/predictions/backtest-history/${runId}`, {
      method: 'GET',
    });
    return response?.data?.item || null;
  }

  async getAIAnalysis(query) {
    const text = String(query || '').trim();
    if (!text) {
      throw new Error('Analysis query is required');
    }

    const response = await this.request('/api/ai/analyze', {
      method: 'POST',
      body: JSON.stringify({ query: text }),
    });
    return response.data;
  }

  async sendAIMessage(message) {
    const text = String(message || '').trim();
    if (!text) {
      throw new Error('Message cannot be empty');
    }

    const response = await this.request('/api/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message: text }),
    });
    return response.data;
  }

  async getHealthStatus() {
    return this.request('/health');
  }

  async getUserProfile() {
    const response = await this.request('/api/user/profile', {
      method: 'GET',
    });
    return response?.data?.user || null;
  }

  async updateUserProfile(profile = {}) {
    const response = await this.request('/api/user/profile', {
      method: 'PUT',
      body: JSON.stringify({ profile }),
    });
    return response?.data?.user || null;
  }

  async updateUserSettings(settings = {}) {
    const response = await this.request('/api/user/settings', {
      method: 'PUT',
      body: JSON.stringify({ settings }),
    });
    return response?.data?.user || null;
  }

  async getInvestmentWatchlist() {
    const response = await this.request('/api/investment/watchlist', { method: 'GET' });
    return response?.data || { symbols: [], config: {} };
  }

  async updateInvestmentWatchlist(symbols = []) {
    const response = await this.request('/api/investment/watchlist', {
      method: 'PUT',
      body: JSON.stringify({ symbols }),
    });
    return response?.data || { symbols: [], config: {} };
  }

  async updatePortfolioConfig(config = {}) {
    const response = await this.request('/api/investment/config', {
      method: 'PUT',
      body: JSON.stringify({ config }),
    });
    return response?.data || config;
  }

  async runPortfolioBacktest(options = {}) {
    const body = {
      symbols: options.symbols,
      weight_mode: options.weight_mode ?? 'equal',
      strategy: options.strategy ?? 'default',
      horizon: options.horizon ?? 5,
      test_size: options.test_size ?? 0.2,
      up_threshold: options.up_threshold ?? 0.02,
      min_confidence: options.min_confidence ?? 0,
      max_symbols: options.max_symbols ?? 10,
    };
    const response = await this.request('/api/investment/portfolio/backtest', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    return response?.data || null;
  }

  async getPaperAccount() {
    const response = await this.request('/api/investment/paper/account', { method: 'GET' });
    return response?.data?.account || null;
  }

  async createPaperAccount(initialCapital) {
    const response = await this.request('/api/investment/paper/account', {
      method: 'POST',
      body: JSON.stringify({ initial_capital: initialCapital }),
    });
    return response?.data?.account || null;
  }

  async advancePaperDay() {
    const response = await this.request('/api/investment/paper/advance-day', { method: 'POST' });
    return response?.data || null;
  }

  async getPaperEquityCurve() {
    const response = await this.request('/api/investment/paper/equity-curve', { method: 'GET' });
    return response?.data || null;
  }

  async getPaperTrades(limit = 50) {
    const response = await this.request('/api/investment/paper/trades', {
      method: 'GET',
      params: { limit },
    });
    return Array.isArray(response?.data?.items) ? response.data.items : [];
  }

  async getSignalStats(symbol, limit = 50) {
    const response = await this.request(`/api/investment/signal-stats/${encodeURIComponent(symbol)}`, {
      method: 'GET',
      params: { limit },
    });
    return response?.data || null;
  }

  async getDailyBrief() {
    const response = await this.request('/api/investment/daily-brief', { method: 'GET' });
    return response?.data || null;
  }

  async getLivePerformance(minSamples = 200) {
    const response = await this.request('/api/investment/live-performance', {
      method: 'GET',
      params: { min_samples: minSamples },
    });
    return response?.data || null;
  }

  async runDailyScreener(options = {}) {
    const response = await this.request('/api/investment/screener/run', {
      method: 'POST',
      body: JSON.stringify({
        top_n: options.topN ?? 5,
        capital: options.capital ?? 100000,
        min_confidence: options.minConfidence ?? 0.55,
      }),
    });
    return response?.data || null;
  }

  async getDailyPicks() {
    const response = await this.request('/api/investment/screener/latest', { method: 'GET' });
    return response?.data || null;
  }

  async getCandidateResearch(symbols = [], options = {}) {
    const response = await this.request('/api/investment/research/candidates', {
      method: 'POST',
      body: JSON.stringify({ symbols, min_score: options.minScore ?? 0.6, top_n: options.topN ?? 10 }),
    });
    return response?.data || null;
  }

  async getHoldingAdvice(holdings = []) {
    const response = await this.request('/api/investment/holdings/advice', {
      method: 'POST', body: JSON.stringify({ holdings }),
    });
    return response?.data || null;
  }

  async getTradingAgentsReview(symbol) {
    const response = await this.request('/api/investment/trading-agents/review', {
      method: 'POST', body: JSON.stringify({ symbol }),
    });
    return response?.data || null;
  }

  async getPortfolioConfig() {
    const response = await this.request('/api/investment/config', { method: 'GET' });
    return response?.data || {};
  }

  async getPortfolioReport(cacheKey) {
    const encoded = encodeURIComponent(cacheKey);
    const response = await this.request(`/api/investment/portfolio/report/${encoded}`, { method: 'GET' });
    return response?.data || null;
  }

  async batchGetStocks(symbols = []) {
    if (!Array.isArray(symbols) || symbols.length === 0) {
      return [];
    }

    const results = await Promise.all(
      symbols.map((symbol) =>
        this.getStockDetail(symbol).catch(() => null)
      )
    );
    return results.filter(Boolean);
  }
}

const stockApiService = new StockApiService();

export default stockApiService;
