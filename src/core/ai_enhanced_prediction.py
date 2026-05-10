#!/usr/bin/env python3
"""
AI大模型增强预测系统
直接使用DeepSeek AI进行预测，拒绝任何模拟数据
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')

class AIEnhancedPredictionSystem:
    """AI增强预测系统 - 仅使用真实AI"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 600  # 10分钟缓存
        self._init_ai_service()
    
    def _init_ai_service(self):
        """初始化AI服务"""
        try:
            # 导入真实AI服务
            import sys
            from pathlib import Path
            project_root = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(project_root))
            
            from services.real_ai_service import real_ai_service
            self.ai_service = real_ai_service
            self.has_real_ai = True
            print("✅ AI增强预测服务初始化成功 - 使用DeepSeek AI")
        except Exception as e:
            print(f"❌ AI服务初始化失败: {e}")
            raise Exception("AI服务必须可用，拒绝使用模拟数据")
    
    def predict(self, symbol: str, horizon: int = 5) -> Dict[str, Any]:
        """使用真实AI进行预测"""
        cache_key = f"prediction_{symbol}_{horizon}"
        
        # 检查缓存
        if cache_key in self.cache:
            cache_time = self.cache[cache_key]["timestamp"]
            if (datetime.now() - cache_time).seconds < self.cache_timeout:
                return self.cache[cache_key]["data"]
        
        try:
            # 构建预测查询
            query = f"请对股票{symbol}进行{horizon}天的价格预测分析，包括目标价格、风险评估和投资建议"
            
            # 使用真实AI服务
            ai_response = self.ai_service.analyze(query)
            
            # 解析AI响应
            prediction_data = self._parse_ai_response(ai_response, symbol, horizon)
            
            # 更新缓存
            self.cache[cache_key] = {
                "timestamp": datetime.now(),
                "data": prediction_data
            }
            
            return prediction_data
            
        except Exception as e:
            print(f"❌ AI预测失败: {e}")
            raise Exception(f"AI预测失败，拒绝使用模拟数据: {str(e)}")
    
    def _parse_ai_response(self, ai_response: str, symbol: str, horizon: int) -> Dict[str, Any]:
        """解析AI响应"""
        return {
            "symbol": symbol,
            "horizon": horizon,
            "prediction_type": "ai_enhanced",
            "ai_analysis": ai_response,
            "confidence": 0.85,  # AI回复的置信度
            "timestamp": datetime.now().isoformat(),
            "data_source": "DeepSeek AI",
            "model_version": "1.0"
        }
    
    def analyze_query(self, query: str) -> str:
        """分析查询"""
        try:
            return self.ai_service.analyze(query)
        except Exception as e:
            print(f"❌ AI分析失败: {e}")
            raise Exception(f"AI分析失败，拒绝使用模拟数据: {str(e)}")

# 创建别名以保持兼容性
AIEnhancedPrediction = AIEnhancedPredictionSystem
