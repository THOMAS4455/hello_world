/**
 * 性能优化工具函数
 */

// 防抖函数
export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

// 节流函数
export const throttle = (func, limit) => {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

// 深度比较对象（用于检测数据变化）
export const deepEqual = (obj1, obj2) => {
  if (obj1 === obj2) return true;
  
  if (obj1 == null || obj2 == null) return false;
  
  if (typeof obj1 !== typeof obj2) return false;
  
  if (typeof obj1 !== 'object') return obj1 === obj2;
  
  const keys1 = Object.keys(obj1);
  const keys2 = Object.keys(obj2);
  
  if (keys1.length !== keys2.length) return false;
  
  for (let key of keys1) {
    if (!keys2.includes(key)) return false;
    if (!deepEqual(obj1[key], obj2[key])) return false;
  }
  
  return true;
};

// 浅比较股票数据
export const compareStockData = (prevStock, currentStock, threshold = 0.01) => {
  if (!prevStock || !currentStock) return false;
  
  const priceDiff = Math.abs(prevStock.current_price - currentStock.current_price);
  const changeDiff = Math.abs(prevStock.change_percent - currentStock.change_percent);
  
  return priceDiff > threshold || changeDiff > threshold;
};

// 批量更新状态
export const batchUpdate = (updates, callback) => {
  requestAnimationFrame(() => {
    callback(updates);
  });
};

// 内存使用监控
export const monitorMemory = () => {
  if (performance.memory) {
    return {
      used: Math.round(performance.memory.usedJSHeapSize / 1048576),
      total: Math.round(performance.memory.totalJSHeapSize / 1048576),
      limit: Math.round(performance.memory.jsHeapSizeLimit / 1048576)
    };
  }
  return null;
};

// 性能计时器
export class PerformanceTimer {
  constructor(name) {
    this.name = name;
    this.startTime = null;
    this.endTime = null;
  }
  
  start() {
    this.startTime = performance.now();
  }
  
  end() {
    this.endTime = performance.now();
    const duration = this.endTime - this.startTime;
    console.log(`${this.name}: ${duration.toFixed(2)}ms`);
    return duration;
  }
}
