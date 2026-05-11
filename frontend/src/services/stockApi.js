import { formatChange, formatPrice, formatVolume } from '../utils/stockUtils';

class StockApiService {
  constructor() {
    this.baseUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    this.cache = new Map();
    this.cacheTimeout = 30000;
  }

  getCacheKey(endpoint, params = {}) {
    return `${endpoint}:${JSON.stringify(params)}`;
  }

  getCachedData(key) {
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
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
    });
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
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') {
        return;
      }
      if (Array.isArray(value)) {
        if (value.length > 0) {
          searchParams.append(key, value.join(','));
        }
        return;
      }
      searchParams.append(key, String(value));
    });
    const query = searchParams.toString();
    return query ? `?${query}` : '';
  }

  getAuthHeaders() {
    try {
      const raw = localStorage.getItem('persist:root');
      if (!raw) {
        return {};
      }
      const parsed = JSON.parse(raw);
      const authState = parsed?.auth ? JSON.parse(parsed.auth) : null;
      const token = authState?.token;
      return token ? { Authorization: `Bearer ${token}` } : {};
    } catch {
      return {};
    }
  }

  normalizeError(status, payload, fallback = 'Request failed') {
    if (payload?.message) {
      return new Error(payload.message);
    }
    return new Error(`${fallback}: ${status}`);
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
    const query = options.params ? this.buildQuery(options.params) : '';
    const url = `${this.baseUrl}${endpoint}${query}`;
    const method = options.method || 'GET';
    const headers = {
      ...this.getAuthHeaders(),
      ...options.headers,
    };

    if (options.body !== undefined && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, {
      method,
      headers,
      body: options.body,
    });

    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }

    if (!response.ok || payload?.success === false) {
      throw this.normalizeError(response.status, payload);
    }

    return payload;
  }

  async getStocks(params = {}) {
    const effectiveParams = {
      limit: 600,
      ...params,
    };
    const cacheKey = this.getCacheKey('/api/stocks', effectiveParams);
    const cached = this.getCachedData(cacheKey);
    if (cached) {
      return cached;
    }

    const response = await this.request('/api/stocks', {
      method: 'GET',
      params: effectiveParams,
    });
    const stocks = Array.isArray(response?.data?.stocks) ? response.data.stocks : [];
    const formattedStocks = stocks.map((stock) => this.normalizeStock(stock));
    this.setCachedData(cacheKey, formattedStocks);
    return formattedStocks;
  }

  async getMarketOverview(params = {}) {
    const cacheKey = this.getCacheKey('/api/stocks/market-overview', params);
    const cached = this.getCachedData(cacheKey);
    if (cached) {
      return cached;
    }

    const response = await this.request('/api/stocks/market-overview', {
      method: 'GET',
      params,
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
      params: { q: keyword },
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

    const params = {
      symbol,
      horizon: options.horizon ?? 5,
      up_threshold: options.upThreshold ?? options.up_threshold ?? 0.02,
    };
    const response = await this.request('/api/predictions/predict', {
      method: 'GET',
      params,
    });
    return response.data;
  }

  async runBacktest(symbol, options = {}) {
    if (!symbol) {
      throw new Error('Stock symbol is required');
    }

    const params = {
      symbol,
      strategy: options.strategy ?? 'default',
      horizon: options.horizon ?? 5,
      test_size: options.testSize ?? options.test_size ?? 0.2,
      up_threshold: options.upThreshold ?? options.up_threshold ?? 0.02,
    };
    const response = await this.request('/api/predictions/backtest', {
      method: 'POST',
      params,
    });
    return response.data;
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

  async getMarketSentiment(symbol = null, options = {}) {
    const params = {
      symbol,
      news_limit: options.newsLimit ?? 20,
      keyword: options.keyword ?? '',
      sources: Array.isArray(options.sources) ? options.sources : ['sina', 'akshare'],
    };
    const forceRefresh = Boolean(options.forceRefresh);
    const cacheKey = this.getCacheKey('/api/sentiment/market', params);
    const cached = this.getCachedData(cacheKey);
    if (cached && !forceRefresh) {
      return cached;
    }

    const response = await this.request('/api/sentiment/market', {
      method: 'GET',
      params,
    });
    this.setCachedData(cacheKey, response.data || null);
    return response.data || null;
  }

  async getHealthStatus() {
    return this.request('/health');
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
