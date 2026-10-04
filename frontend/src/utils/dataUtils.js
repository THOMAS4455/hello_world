/**
 * 数据验证和处理工具
 */

/**
 * 确保返回数组格式的股票数据
 * @param {any} data - API返回的数据
 * @returns {Array} 股票数组
 */
export const ensureStocksArray = (data) => {
  if (data && data.data && Array.isArray(data.data)) {
    return data.data;
  } else if (Array.isArray(data)) {
    return data;
  } else if (data && typeof data === 'object') {
    // 尝试从对象中提取数组
    const possibleArrays = Object.values(data).filter(value => Array.isArray(value));
    if (possibleArrays.length > 0) {
      return possibleArrays[0];
    }
  }
  
  console.warn('Invalid stocks data structure:', data);
  return [];
};

/**
 * 确保返回数组格式的预测数据
 * @param {any} data - API返回的数据
 * @returns {Array} 预测数组
 */
export const ensurePredictionsArray = (data) => {
  if (data && data.data && Array.isArray(data.data)) {
    return data.data;
  } else if (Array.isArray(data)) {
    return data;
  } else if (data && typeof data === 'object') {
    const possibleArrays = Object.values(data).filter(value => Array.isArray(value));
    if (possibleArrays.length > 0) {
      return possibleArrays[0];
    }
  }
  
  console.warn('Invalid predictions data structure:', data);
  return [];
};

/**
 * 确保返回数组格式的新闻数据
 * @param {any} data - API返回的数据
 * @returns {Array} 新闻数组
 */
export const ensureNewsArray = (data) => {
  if (data && data.data && Array.isArray(data.data)) {
    return data.data;
  } else if (Array.isArray(data)) {
    return data;
  } else if (data && typeof data === 'object') {
    const possibleArrays = Object.values(data).filter(value => Array.isArray(value));
    if (possibleArrays.length > 0) {
      return possibleArrays[0];
    }
  }
  
  console.warn('Invalid news data structure:', data);
  return [];
};

/**
 * 安全地获取数据字段
 * @param {Object} obj - 数据对象
 * @param {string} path - 字段路径 (如 'data.stocks')
 * @param {any} defaultValue - 默认值
 * @returns {any} 字段值或默认值
 */
export const safeGet = (obj, path, defaultValue = null) => {
  if (!obj || typeof obj !== 'object') {
    return defaultValue;
  }
  
  const keys = path.split('.');
  let current = obj;
  
  for (const key of keys) {
    if (current && typeof current === 'object' && key in current) {
      current = current[key];
    } else {
      return defaultValue;
    }
  }
  
  return current;
};

/**
 * 格式化股票价格显示
 * @param {number} price - 价格
 * @returns {string} 格式化后的价格
 */
export const formatPrice = (price) => {
  if (typeof price !== 'number' || isNaN(price)) {
    return 'N/A';
  }
  return `$${price.toFixed(2)}`;
};

/**
 * 格式化百分比显示
 * @param {number} percent - 百分比
 * @returns {string} 格式化后的百分比
 */
export const formatPercent = (percent) => {
  if (typeof percent !== 'number' || isNaN(percent)) {
    return 'N/A';
  }
  return `${percent.toFixed(2)}%`;
};

/**
 * 获取涨跌状态的CSS类名
 * @param {number} value - 数值
 * @returns {string} CSS类名
 */
export const getChangeClass = (value) => {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '';
  }
  if (value === 0) {
    return 'market-flat';
  }
  return value > 0 ? 'market-up' : 'market-down';
};
