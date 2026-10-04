/**
 * 股票相关工具函数
 */

/**
 * 格式化股票价格
 * @param {number} price - 股票价格
 * @param {number} decimals - 小数位数
 * @returns {string} 格式化后的价格
 */
export const formatPrice = (price, decimals = 2) => {
  if (typeof price !== 'number' || isNaN(price)) {
    return '¥0.00';
  }
  return `¥${price.toFixed(decimals)}`;
};

/**
 * 格式化涨跌幅
 * @param {number} change - 涨跌额
 * @param {number} changePercent - 涨跌幅
 * @returns {object} 格式化后的涨跌信息
 */
/** A-share convention: up = red, down = green */
export const MARKET_UP_COLOR = '#e5484d';
export const MARKET_DOWN_COLOR = '#30a46c';

export const isMarketUp = (value) => Number(value) > 0;
export const isMarketDown = (value) => Number(value) < 0;

export const getMarketChangeClass = (value = 0) => {
  const num = Number(value);
  if (Number.isNaN(num) || num === 0) {
    return 'market-flat';
  }
  return num > 0 ? 'market-up' : 'market-down';
};

export const getMarketBadgeClass = (value = 0) => {
  const num = Number(value);
  if (Number.isNaN(num) || num === 0) {
    return 'bg-secondary';
  }
  return num > 0 ? 'bg-market-up' : 'bg-market-down';
};

export const getMarketDirectionBadge = (direction) => {
  if (direction === 'up' || direction === 'bullish' || direction === 1 || direction === '1') {
    return 'bg-market-up';
  }
  if (direction === 'down' || direction === 'bearish' || direction === 0 || direction === '0') {
    return 'bg-market-down';
  }
  return 'bg-secondary';
};

export const formatChange = (change, changePercent) => {
  const isPositive = change >= 0;
  const sign = isPositive ? '+' : '';

  return {
    change: `${sign}${change.toFixed(2)}`,
    changePercent: `${sign}${changePercent.toFixed(2)}%`,
    isPositive,
    color: getMarketChangeClass(change),
    sign,
  };
};

/**
 * 格式化成交量
 * @param {number} volume - 成交量
 * @returns {string} 格式化后的成交量
 */
export const formatVolume = (volume) => {
  if (typeof volume !== 'number' || isNaN(volume)) {
    return '0';
  }
  
  if (volume >= 100000000) {
    return `${(volume / 100000000).toFixed(1)}亿`;
  } else if (volume >= 10000) {
    return `${(volume / 10000).toFixed(1)}万`;
  } else {
    return volume.toLocaleString();
  }
};

/**
 * 格式化市值
 * @param {number} marketCap - 市值
 * @returns {string} 格式化后的市值
 */
export const formatMarketCap = (marketCap) => {
  if (typeof marketCap !== 'number' || isNaN(marketCap) || marketCap === 0) {
    return '未知';
  }
  
  if (marketCap >= 100000000000) {
    return `${(marketCap / 100000000000).toFixed(1)}千亿`;
  } else if (marketCap >= 100000000) {
    return `${(marketCap / 100000000).toFixed(1)}亿`;
  } else if (marketCap >= 10000) {
    return `${(marketCap / 10000).toFixed(1)}万`;
  } else {
    return marketCap.toLocaleString();
  }
};

/**
 * 获取股票状态颜色
 * @param {object} stock - 股票对象
 * @returns {string} 颜色类名
 */
export const getStockColor = (stock) => {
  if (!stock || typeof stock.change !== 'number') {
    return 'secondary';
  }
  return getMarketBadgeClass(stock.change);
};

/**
 * 计算股票排名
 * @param {array} stocks - 股票数组
 * @param {string} sortBy - 排序字段
 * @param {string} order - 排序方向
 * @returns {array} 排序后的股票数组
 */
export const rankStocks = (stocks, sortBy = 'change_percent', order = 'desc') => {
  if (!Array.isArray(stocks)) {
    return [];
  }
  
  return [...stocks]
    .sort((a, b) => {
      const aValue = a[sortBy] || 0;
      const bValue = b[sortBy] || 0;
      
      if (order === 'desc') {
        return bValue - aValue;
      } else {
        return aValue - bValue;
      }
    })
    .map((stock, index) => ({
      ...stock,
      rank: index + 1
    }));
};

/**
 * 获取股票统计信息
 * @param {array} stocks - 股票数组
 * @returns {object} 统计信息
 */
export const getStockStats = (stocks) => {
  if (!Array.isArray(stocks) || stocks.length === 0) {
    return {
      total: 0,
      up: 0,
      down: 0,
      flat: 0,
      upPercent: 0,
      downPercent: 0,
      flatPercent: 0,
      avgChange: 0,
      maxChange: 0,
      minChange: 0
    };
  }
  
  const up = stocks.filter(stock => stock.change > 0).length;
  const down = stocks.filter(stock => stock.change < 0).length;
  const flat = stocks.filter(stock => stock.change === 0).length;
  const total = stocks.length;
  
  const changes = stocks.map(stock => stock.change || 0);
  const avgChange = changes.reduce((sum, change) => sum + change, 0) / total;
  const maxChange = Math.max(...changes);
  const minChange = Math.min(...changes);
  
  return {
    total,
    up,
    down,
    flat,
    upPercent: (up / total * 100).toFixed(1),
    downPercent: (down / total * 100).toFixed(1),
    flatPercent: (flat / total * 100).toFixed(1),
    avgChange: avgChange.toFixed(2),
    maxChange: maxChange.toFixed(2),
    minChange: minChange.toFixed(2)
  };
};

/**
 * 搜索股票
 * @param {array} stocks - 股票数组
 * @param {string} searchTerm - 搜索词
 * @returns {array} 过滤后的股票数组
 */
export const searchStocks = (stocks, searchTerm) => {
  if (!Array.isArray(stocks) || !searchTerm) {
    return stocks;
  }
  
  const term = searchTerm.toLowerCase().trim();
  
  return stocks.filter(stock => {
    const symbol = (stock.symbol || '').toLowerCase();
    const name = (stock.name || '').toLowerCase();
    
    return symbol.includes(term) || name.includes(term);
  });
};

/**
 * 过滤股票
 * @param {array} stocks - 股票数组
 * @param {object} filters - 过滤条件
 * @returns {array} 过滤后的股票数组
 */
export const filterStocks = (stocks, filters) => {
  if (!Array.isArray(stocks)) {
    return [];
  }
  
  return stocks.filter(stock => {
    // 价格区间过滤
    if (filters.priceRange) {
      const { min, max } = filters.priceRange;
      if (stock.price < min || stock.price > max) {
        return false;
      }
    }
    
    // 涨跌幅过滤
    if (filters.changeRange) {
      const { min, max } = filters.changeRange;
      if (stock.change_percent < min || stock.change_percent > max) {
        return false;
      }
    }
    
    // 成交量过滤
    if (filters.volumeMin && stock.volume < filters.volumeMin) {
      return false;
    }
    
    // 涨跌状态过滤
    if (filters.status && filters.status !== 'all') {
      if (filters.status === 'up' && stock.change <= 0) return false;
      if (filters.status === 'down' && stock.change >= 0) return false;
      if (filters.status === 'flat' && stock.change !== 0) return false;
    }
    
    return true;
  });
};

/**
 * 生成股票历史数据
 * @param {number} currentPrice - 当前价格
 * @param {number} days - 天数
 * @returns {array} 历史数据数组
 */
export const generateHistoricalData = (currentPrice, days = 30) => {
  const data = [];
  let price = currentPrice * 0.9; // 从90%开始
  
  for (let i = 0; i < days; i++) {
    const change = (Math.random() - 0.5) * currentPrice * 0.05; // ±5%变化
    price += change;
    
    data.push({
      date: new Date(Date.now() - (days - i) * 24 * 60 * 60 * 1000),
      price: Math.max(price, 0), // 确保价格不为负
      volume: Math.floor(Math.random() * 1000000) + 100000,
      high: price * (1 + Math.random() * 0.02),
      low: price * (1 - Math.random() * 0.02),
      open: price * (1 + (Math.random() - 0.5) * 0.01)
    });
  }
  
  return data;
};

/**
 * 验证股票数据
 * @param {object} stock - 股票对象
 * @returns {boolean} 是否有效
 */
export const validateStock = (stock) => {
  if (!stock || typeof stock !== 'object') {
    return false;
  }
  
  const requiredFields = ['symbol', 'name', 'price'];
  
  return requiredFields.every(field => {
    const value = stock[field];
    return value !== undefined && value !== null && value !== '';
  });
};

/**
 * 获取股票建议
 * @param {object} stock - 股票对象
 * @returns {object} 建议信息
 */
export const getStockAdvice = (stock) => {
  if (!validateStock(stock)) {
    return { advice: '数据无效', color: 'secondary', icon: '❓' };
  }
  
  const changePercent = stock.change_percent || 0;
  
  if (changePercent > 5) {
    return { advice: '强势上涨', color: 'success', icon: '🚀' };
  } else if (changePercent > 2) {
    return { advice: '温和上涨', color: 'info', icon: '📈' };
  } else if (changePercent > -2) {
    return { advice: '震荡整理', color: 'warning', icon: '➰' };
  } else if (changePercent > -5) {
    return { advice: '温和下跌', color: 'secondary', icon: '📉' };
  } else {
    return { advice: '大幅下跌', color: 'danger', icon: '⚠️' };
  }
};

/**
 * 格式化时间
 * @param {Date|string} date - 日期
 * @param {string} format - 格式化类型
 * @returns {string} 格式化后的时间
 */
export const formatTime = (date, format = 'datetime') => {
  const d = new Date(date);
  
  if (isNaN(d.getTime())) {
    return '无效时间';
  }
  
  switch (format) {
    case 'date':
      return d.toLocaleDateString('zh-CN');
    case 'time':
      return d.toLocaleTimeString('zh-CN');
    case 'datetime':
      return d.toLocaleString('zh-CN');
    case 'iso':
      return d.toISOString();
    default:
      return d.toLocaleString('zh-CN');
  }
};

/**
 * 防抖函数
 * @param {function} func - 要防抖的函数
 * @param {number} delay - 延迟时间
 * @returns {function} 防抖后的函数
 */
export const debounce = (func, delay) => {
  let timeoutId;
  
  return function (...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(this, args), delay);
  };
};

/**
 * 节流函数
 * @param {function} func - 要节流的函数
 * @param {number} delay - 延迟时间
 * @returns {function} 节流后的函数
 */
export const throttle = (func, delay) => {
  let lastCall = 0;
  
  return function (...args) {
    const now = Date.now();
    
    if (now - lastCall >= delay) {
      lastCall = now;
      return func.apply(this, args);
    }
  };
};

/**
 * Normalize A-share symbol to a 6-digit code (e.g. sz000001 -> 000001).
 * @param {string} raw
 * @returns {string|null}
 */
export const normalizeAshareSymbol = (raw) => {
  const text = String(raw || '').trim().toUpperCase();
  if (!text) {
    return null;
  }
  const stripped = text.replace(/^(SH|SZ|BJ)/i, '').replace(/\.(SH|SZ|BJ)$/i, '');
  const match = stripped.match(/\d{6}/);
  return match ? match[0] : null;
};
