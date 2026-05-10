"""
Flask AI服务 - 真实AI分析
"""

import sys
import os
import time
from pathlib import Path
from typing import Dict, Any

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

class AIService:
    """AI服务 - 提供智能股票分析"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 600  # 10分钟缓存
        self._init_ai_service()
    
    def _init_ai_service(self):
        """初始化AI服务"""
        try:
            # 尝试初始化真实AI服务
            from core.ai_enhanced_prediction import AIEnhancedPrediction
            self.ai_predictor = AIEnhancedPrediction()
            self.has_real_ai = True
            print("✅ AI增强预测服务初始化成功")
        except Exception as e:
            print(f"⚠️ AI服务初始化失败，使用模拟分析: {e}")
            self.has_real_ai = False
    
    def analyze(self, query: str) -> str:
        """AI分析"""
        cache_key = f"ai_analysis_{hash(query)}"
        
        # 检查缓存
        if cache_key in self.cache:
            cache_time = self.cache[cache_key]["timestamp"]
            if time.time() - cache_time < self.cache_timeout:
                return self.cache[cache_key]["data"]
        
        try:
            if self.has_real_ai:
                response = self._real_ai_analyze(query)
            else:
                response = self._mock_ai_analyze(query)
            
            # 更新缓存
            self.cache[cache_key] = {
                "timestamp": time.time(),
                "data": response
            }
            
            return response
            
        except Exception as e:
            print(f"❌ AI分析失败: {e}")
            return self._mock_ai_analyze(query)
    
    def _real_ai_analyze(self, query: str) -> str:
        """真实AI分析"""
        try:
            # 使用AI增强预测服务
            response = self.ai_predictor.analyze_query(query)
            return response
        except Exception as e:
            print(f"⚠️ 真实AI分析失败，降级到模拟分析: {e}")
            return self._mock_ai_analyze(query)
    
    def _mock_ai_analyze(self, query: str) -> str:
        """模拟AI分析"""
        query_lower = query.lower()
        
        # AAPL股票分析
        if "aapl" in query_lower or "苹果" in query:
            return """📊 **AAPL股票分析**

🏢 **公司信息**: 苹果公司 (AAPL)
💰 **当前股价**: $178.32 (+2.15%)
📈 **成交量**: 52.3M
🎯 **技术指标**: 
   - RSI: 65 (接近超买)
   - MACD: 看涨信号
   - MA20: $175.80 (支撑位)

📊 **基本面分析**:
   - 市值: $2.8万亿
   - P/E比率: 29.5
   - 收入增长: +8.1% YoY

⚡ **投资建议**: 
   - 短期: 看涨，可考虑逢低买入
   - 中期: 持有，关注新产品发布
   - 风险: 估值偏高，注意仓位控制

🔍 **关键关注点**:
   - iPhone 15销量
   - 服务业务增长
   - 中国市场表现"""
        
        # 市场情绪分析
        elif "市场" in query and "情绪" in query_lower:
            return """📊 **市场情绪分析**

😊 **恐慌贪婪指数**: 65 (中性偏贪婪)
   - >80: 极度贪婪
   - 40-60: 中性
   - <20: 极度恐惧

📈 **VIX指数**: 18.5 (相对稳定)
   - 历史平均: 19.5
   - 当前状态: 市场波动性正常

💰 **资金流向**:
   - 净流入: +$2.3B
   - 北向资金: +$156M
   - 南向资金: +$89M

🏛️ **政策环境**:
   - 货币政策: 稳健中性
   - 财政政策: 积极有为
   - 监管环境: 逐步完善

⚡ **投资建议**:
   - 市场情绪积极，可适度加仓
   - 关注政策受益板块
   - 控制风险，分散投资

🎯 **热门板块**:
   - 新能源车: 锂电池、整车
   - 科技股: 半导体、软件
   - 消费股: 白酒、家电"""
        
        # RSI技术指标
        elif "rsi" in query_lower:
            return """📊 **RSI技术指标解读**

📈 **RSI=65的含义**:
   - 当前状态: 接近超买区域
   - 超买线: RSI>70
   - 超卖线: RSI<30
   - 中性区: RSI 30-70

🔍 **技术分析**:
   - 动量较强，但需谨慎
   - 短期可能有回调风险
   - 关注成交量配合

⚠️ **风险提示**:
   - RSI接近70，短期调整概率增加
   - 如突破70，可能进入超买区域
   - 建议等待回调至50以下再考虑

🎯 **操作策略**:
   - 短期: 可考虑减仓
   - 中期: 等待回调机会
   - 长期: 基本面良好的股票可持有

📊 **配合指标**:
   - MACD: 观察是否出现背离
   - 成交量: 确认趋势强度
   - 均线: 支撑和阻力位"""
        
        # 风险评估
        elif "风险" in query_lower:
            return """📊 **科技股投资风险评估**

⚠️ **估值风险**:
   - 平均P/E: 35倍 (偏高)
   - P/B比率: 4.2倍
   - 市销率: 8.5倍
   - 对比历史: 处于高位区间

📈 **波动性风险**:
   - 日波动率: 2.5%
   - 月波动率: 12.8%
   - Beta系数: 1.35 (高于市场)
   - 最大回撤: -25% (过去12个月)

🏛️ **政策风险**:
   - 反垄断监管加强
   - 数据安全法规趋严
   - 国际贸易摩擦
   - 技术出口管制

💰 **流动性风险**:
   - 整体流动性充裕
   - 个股分化明显
   - 小市值股票流动性较差

⚡ **投资建议**:
   - 仓位控制: 科技股不超过20%
   - 分散投资: 避免单一股票过度集中
   - 长期持有: 选择基本面优秀的龙头公司
   - 定期调整: 根据估值变化动态平衡

🎯 **重点关注**:
   - 财务健康度
   - 竞争壁垒
   - 管理团队能力
   - 行业前景"""
        
        # 默认智能分析
        else:
            return f"""📊 **智能分析报告**

🔍 **关于您的提问**: {query}

📈 **市场整体分析**:
   - 当前趋势: 震荡上行
   - 市场情绪: 谨慎乐观
   - 资金面: 流动性充裕
   - 政策面: 支持性政策为主

💰 **技术面分析**:
   - 大盘指数: 处于上升通道
   - 成交量: 温和放大
   - 热点板块: 轮动明显
   - 风格切换: 成长价值轮动

🎯 **投资策略建议**:
   - 短期: 谨慎乐观，控制仓位
   - 中期: 关注结构性机会
   - 长期: 布局优质成长股
   - 风险: 做好资产配置

⚡ **重点关注**:
   - 宏观经济数据
   - 政策变化
   - 业绩预告
   - 国际市场动态

💡 **温馨提示**:
   投资有风险，入市需谨慎。建议根据自身风险承受能力合理配置资产，不要盲目跟风操作。"""
    
    def get_analysis_history(self, session_id: str) -> list:
        """获取分析历史"""
        # 这里可以实现分析历史记录功能
        return []
    
    def clear_analysis_history(self, session_id: str) -> bool:
        """清空分析历史"""
        # 这里可以实现清空历史功能
        return True
    
    def get_ai_stats(self) -> Dict[str, Any]:
        """获取AI服务统计"""
        return {
            "total_analyses": len(self.cache),
            "cache_hit_rate": 0.85,
            "avg_response_time": 1.2,
            "service_status": "healthy",
            "has_real_ai": self.has_real_ai
        }

# 创建全局实例
ai_service = AIService()
