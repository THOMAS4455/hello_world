/**
 * 股票API服务
 * 统一管理所有股票相关的API调用
 */

import { formatPrice, formatChange, formatVolume } from '../utils/stockUtils';

class StockApiService {
  constructor() {
    this.baseUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
    this.cache = new Map();
    this.cacheTimeout = 30000; // 30秒缓存
  }

  /**
   * 获取缓存键
   * @param {string} endpoint - API端点
   * @param {object} params - 参数
   * @returns {string} 缓存键
   */
  getCacheKey(endpoint, params = {}) {
    return `${endpoint}:${JSON.stringify(params)}`;
  }

  /**
   * 检查缓存
   * @param {string} key - 缓存键
   * @returns {object|null} 缓存数据或null
   */
  getCachedData(key) {
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.data;
    }
    return null;
  }

  /**
   * 设置缓存
   * @param {string} key - 缓存键
   * @param {any} data - 数据
   */
  setCachedData(key, data) {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });
  }

  /**
   * 清除缓存
   * @param {string} pattern - 清除模式
   */
  clearCache(pattern = null) {
    if (pattern) {
      for (const key of this.cache.keys()) {
        if (key.includes(pattern)) {
          this.cache.delete(key);
        }
      }
    } else {
      this.cache.clear();
    }
  }

  /**
   * 通用API请求
   * @param {string} endpoint - API端点
   * @param {object} options - 请求选项
   * @returns {Promise} API响应
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('API请求错误:', error);
      throw error;
    }
  }

  /**
   * 获取股票列表
   * @param {object} params - 查询参数
   * @returns {Promise} 股票列表
   */
  async getStocks(params = {}) {
    const effectiveParams = {
      limit: 600,
      ...params
    };
    const cacheKey = this.getCacheKey('/api/stocks', effectiveParams);
    const cached = this.getCachedData(cacheKey);
    
    if (cached) {
      return cached;
    }

    try {
      const searchParams = new URLSearchParams();
      Object.entries(effectiveParams).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') {
          searchParams.append(k, String(v));
        }
      });
      const query = searchParams.toString();
      const endpoint = query ? `/api/stocks?${query}` : '/api/stocks';

      const response = await this.request(endpoint, {
        method: 'GET'
      });

      const stocks = response.data?.stocks || [];
      
      // 格式化股票数据
      const formattedStocks = stocks.map(stock => ({
        ...stock,
        formattedPrice: formatPrice(stock.price),
        formattedChange: formatChange(stock.change, stock.change_percent),
        formattedVolume: formatVolume(stock.volume)
      }));

      this.setCachedData(cacheKey, formattedStocks);
      return formattedStocks;
    } catch (error) {
      console.error('获取股票列表失败:', error);
      throw error;
    }
  }

  /**
   * 获取股票详情
   * @param {string} symbol - 股票代码
   * @returns {Promise} 股票详情
   */
  async getStockDetail(symbol) {
    if (!symbol) {
      throw new Error('股票代码不能为空');
    }

    const cacheKey = this.getCacheKey(`/api/stocks/${symbol}`);
    const cached = this.getCachedData(cacheKey);
    
    if (cached) {
      return cached;
    }

    try {
      const response = await this.request(`/api/stocks/${symbol}`);
      
      if (!response.success) {
        throw new Error(response.message || '获取股票详情失败');
      }

      const stock = response.data;
      
      // 格式化股票数据
      const formattedStock = {
        ...stock,
        formattedPrice: formatPrice(stock.price),
        formattedChange: formatChange(stock.change, stock.change_percent),
        formattedVolume: formatVolume(stock.volume)
      };

      this.setCachedData(cacheKey, formattedStock);
      return formattedStock;
    } catch (error) {
      console.error('获取股票详情失败:', error);
      throw error;
    }
  }

  /**
   * 搜索股票
   * @param {string} query - 搜索关键词
   * @returns {Promise} 搜索结果
   */
  async searchStocks(query) {
    if (!query || query.trim().length === 0) {
      return [];
    }

    const cacheKey = this.getCacheKey('/api/stocks/search', { query });
    const cached = this.getCachedData(cacheKey);
    
    if (cached) {
      return cached;
    }

    try {
      const response = await this.request('/api/stocks/search', {
        method: 'POST',
        body: JSON.stringify({ query })
      });

      const stocks = response.data?.stocks || [];
      
      // 格式化股票数据
      const formattedStocks = stocks.map(stock => ({
        ...stock,
        formattedPrice: formatPrice(stock.price),
        formattedChange: formatChange(stock.change, stock.change_percent),
        formattedVolume: formatVolume(stock.volume)
      }));

      this.setCachedData(cacheKey, formattedStocks);
      return formattedStocks;
    } catch (error) {
      console.error('搜索股票失败:', error);
      throw error;
    }
  }

  /**
   * 获取实时股票数据
   * @param {array} symbols - 股票代码数组
   * @returns {Promise} 实时数据
   */
  async getRealTimeStocks(symbols = []) {
    if (!Array.isArray(symbols) || symbols.length === 0) {
      return [];
    }

    const cacheKey = this.getCacheKey('/api/stocks/realtime', { symbols });
    const cached = this.getCachedData(cacheKey);
    
    if (cached) {
      return cached;
    }

    try {
      const response = await this.request('/api/stocks/realtime', {
        method: 'POST',
        body: JSON.stringify({ symbols })
      });

      const stocks = response.data?.stocks || [];
      
      // 格式化股票数据
      const formattedStocks = stocks.map(stock => ({
        ...stock,
        formattedPrice: formatPrice(stock.price),
        formattedChange: formatChange(stock.change, stock.change_percent),
        formattedVolume: formatVolume(stock.volume)
      }));

      this.setCachedData(cacheKey, formattedStocks);
      return formattedStocks;
    } catch (error) {
      console.error('获取实时股票数据失败:', error);
      throw error;
    }
  }

  /**
   * 获取股票预测
   * @param {string} symbol - 股票代码
   * @param {object} options - 预测选项
   * @returns {Promise} 预测结果
   */
  async getStockPrediction(symbol, options = {}) {
    if (!symbol) {
      throw new Error('股票代码不能为空');
    }

    try {
      const response = await this.request('/api/ai/predict', {
        method: 'POST',
        body: JSON.stringify({
          symbol,
          ...options
        })
      });

      if (!response.success) {
        throw new Error(response.message || '获取预测失败');
      }

      return response.data;
    } catch (error) {
      console.error('获取股票预测失败:', error);
      throw error;
    }
  }

  /**
   * 获取AI分析
   * @param {string} symbol - 股票代码
   * @param {string} analysisType - 分析类型
   * @returns {Promise} 分析结果
   */
  async getAIAnalysis(symbol, analysisType = 'basic') {
    if (!symbol) {
      throw new Error('股票代码不能为空');
    }

    try {
      const response = await this.request('/api/ai/analyze', {
        method: 'POST',
        body: JSON.stringify({
          symbol,
          analysis_type: analysisType
        })
      });

      if (!response.success) {
        throw new Error(response.message || '获取AI分析失败');
      }

      return response.data;
    } catch (error) {
      console.error('获取AI分析失败:', error);
      throw error;
    }
  }

  /**
   * 发送AI聊天消息
   * @param {string} message - 消息内容
   * @param {object} context - 上下文信息
   * @returns {Promise} AI回复
   */
  async sendAIMessage(message, context = {}) {
    if (!message || message.trim().length === 0) {
      throw new Error('消息内容不能为空');
    }

    try {
      const response = await this.request('/api/ai/chat', {
        method: 'POST',
        body: JSON.stringify({
          message,
          context
        })
      });

      if (!response.success) {
        throw new Error(response.message || '发送消息失败');
      }

      return response.data;
    } catch (error) {
      console.error('发送AI消息失败:', error);
      throw error;
    }
  }

  /**
   * 获取市场情绪分析
   * @param {string} symbol - 股票代码（可选）
   * @returns {Promise} 情绪分析结果
   */
  async getMarketSentiment(symbol = null, options = {}) {
    const forceRefresh = Boolean(options?.forceRefresh);
    const newsLimit = options?.newsLimit ?? 20;
    const keyword = options?.keyword ?? '';
    const sources = Array.isArray(options?.sources) ? options.sources : ['sina', 'akshare'];
    const cacheKey = this.getCacheKey('/api/sentiment/market', { symbol, newsLimit, keyword, sources });
    const cached = this.getCachedData(cacheKey);
    
    if (cached && !forceRefresh) {
      return cached;
    }

    try {
      const params = new URLSearchParams();
      if (symbol) {
        params.append('symbol', String(symbol));
      }
      params.append('news_limit', String(newsLimit));
      if (keyword && String(keyword).trim()) {
        params.append('keyword', String(keyword).trim());
      }
      if (sources.length > 0) {
        params.append('sources', sources.join(','));
      }
      const endpoint = `/api/sentiment/market?${params.toString()}`;
      const response = await this.request(endpoint, {
        method: 'GET'
      });

      if (!response?.success || !response?.data) {
        throw new Error(response?.message || '获取市场情绪失败');
      }

      this.setCachedData(cacheKey, response.data);
      return response.data;
    } catch (error) {
      console.error('获取市场情绪失败:', error);
      throw error;
    }
  }

  /**
   * 获取系统健康状态
   * @returns {Promise} 系统状态
   */
  async getHealthStatus() {
    try {
      const response = await this.request('/health');
      return response;
    } catch (error) {
      console.error('获取系统状态失败:', error);
      throw error;
    }
  }

  /**
   * 批量获取股票数据
   * @param {array} symbols - 股票代码数组
   * @returns {Promise} 股票数据数组
   */
  async batchGetStocks(symbols) {
    if (!Array.isArray(symbols) || symbols.length === 0) {
      return [];
    }

    try {
      const promises = symbols.map(symbol => 
        this.getStockDetail(symbol).catch(error => {
          console.error(`获取股票 ${symbol} 详情失败:`, error);
          return null;
        })
      );

      const results = await Promise.all(promises);
      return results.filter(stock => stock !== null);
    } catch (error) {
      console.error('批量获取股票数据失败:', error);
      throw error;
    }
  }

  /**
   * 获取股票历史数据
   * @param {string} symbol - 股票代码
   * @param {object} options - 查询选项
   * @returns {Promise} 历史数据
   */
  async getStockHistory(symbol, options = {}) {
    if (!symbol) {
      throw new Error('股票代码不能为空');
    }

    const cacheKey = this.getCacheKey(`/api/stocks/${symbol}/history`, options);
    const cached = this.getCachedData(cacheKey);
    
    if (cached) {
      return cached;
    }

    try {
      const response = await this.request(`/api/stocks/${symbol}/history`, {
        method: 'POST',
        body: JSON.stringify(options)
      });

      this.setCachedData(cacheKey, response.data);
      return response.data;
    } catch (error) {
      console.error('获取股票历史数据失败:', error);
      throw error;
    }
  }
}

// 创建单例实例
const stockApiService = new StockApiService();

export default stockApiService;
