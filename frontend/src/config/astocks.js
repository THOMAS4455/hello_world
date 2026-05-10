export const ASTOCKS_CONFIG = {
  market: 'A股',
  currency: '¥',
  marketName: '中国A股',
  timezone: 'Asia/Shanghai',
  tradingHours: '09:30-15:00',
  tradingDays: '周一至周五',
  priceUnit: '人民币',
  limitUpDown: '±10%',
  tradingSystem: 'T+1',
  exchanges: {
    '000': '深交所',
    '002': '深交所', 
    '300': '深交所',
    '600': '上交所',
    '601': '上交所',
    '603': '上交所'
  },
  sectors: {
    '金融': 'finance',
    '消费': 'consumer',
    '科技': 'technology',
    '新能源': 'new_energy',
    '医疗': 'healthcare',
    '房地产': 'real_estate',
    '汽车': 'automotive',
    '金融科技': 'fintech'
  }
};

export const formatAStockPrice = (price) => {
  return `¥${price?.toFixed(2) || '0.00'}`;
};

export const formatAStockChange = (change) => {
  if (!change) return '0.00%';
  const changeStr = change > 0 ? `+${change.toFixed(2)}%` : `${change.toFixed(2)}%`;
  return changeStr;
};

export const getExchange = (symbol) => {
  const prefix = symbol.substring(0, 3);
  return ASTOCKS_CONFIG.exchanges[prefix] || '未知';
};

export const isLimitUp = (changePercent) => {
  return changePercent >= 9.8; // 接近涨停
};

export const isLimitDown = (changePercent) => {
  return changePercent <= -9.8; // 接近跌停
};
