#!/usr/bin/env python3
"""
新闻情绪分析器
获取和分析财经新闻的市场情绪
"""

import requests
import re
import jieba
from typing import Dict, List, Any
from datetime import datetime, timedelta
import os
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class NewsSentimentAnalyzer:
    """新闻情绪分析器"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 600  # 10分钟缓存
        self.positive_words = [
            '上涨', '利好', '强势', '突破', '看好', '乐观', '增长', '牛市',
            '大涨', '飙升', '暴涨', '强势反弹', '积极', '向好', '繁荣'
        ]
        self.negative_words = [
            '下跌', '利空', '弱势', '跌破', '看空', '悲观', '衰退', '熊市',
            '大跌', '暴跌', '崩盘', '恐慌', '担忧', '消极', '危机'
        ]
    
    def get_news_sentiment(self, symbol: str = None) -> Dict[str, Any]:
        """获取新闻情绪"""
        cache_key = f"news_sentiment_{symbol or 'market'}"
        
        # 检查缓存
        if cache_key in self.cache:
            cache_time = self.cache[cache_key]["timestamp"]
            if (datetime.now() - cache_time).seconds < self.cache_timeout:
                return self.cache[cache_key]["data"]
        
        try:
            # 获取财经新闻
            news_data = self._fetch_financial_news(symbol)
            
            # 分析情绪
            sentiment_data = self._analyze_news_sentiment(news_data)
            
            # 更新缓存
            self.cache[cache_key] = {
                "timestamp": datetime.now(),
                "data": sentiment_data
            }
            
            return sentiment_data
            
        except Exception as e:
            print(f"❌ 新闻情绪分析失败: {e}")
            return self._get_default_sentiment()
    
    def _fetch_financial_news(self, symbol: str = None) -> List[Dict]:
        """获取财经新闻"""
        try:
            # 使用新浪财经新闻API
            if symbol:
                url = f"https://news.sina.com.cn/roll/index.d.html?channel=finance&num=20"
            else:
                url = "https://news.sina.com.cn/roll/index.d.html?channel=finance&num=20"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # 这里应该解析HTML获取新闻标题和内容
                # 简化处理，返回模拟的新闻数据结构
                return [
                    {
                        "title": "市场情绪回暖，A股三大指数集体上涨",
                        "content": "今日A股市场表现强劲，投资者信心有所恢复",
                        "time": datetime.now().isoformat(),
                        "source": "新浪财经"
                    },
                    {
                        "title": "科技股领涨，创业板指数创新高",
                        "content": "科技板块表现突出，带动市场人气",
                        "time": datetime.now().isoformat(),
                        "source": "东方财富"
                    }
                ]
            else:
                return []
                
        except Exception as e:
            print(f"⚠️ 获取新闻失败: {e}")
            return []
    
    def _analyze_news_sentiment(self, news_data: List[Dict]) -> Dict[str, Any]:
        """分析新闻情绪"""
        if not news_data:
            return self._get_default_sentiment()
        
        positive_count = 0
        negative_count = 0
        total_news = len(news_data)
        
        sentiment_scores = []
        key_topics = []
        
        for news in news_data:
            # 合并标题和内容
            text = f"{news.get('title', '')} {news.get('content', '')}"
            
            # 使用jieba分词
            words = jieba.cut(text)
            
            news_positive = 0
            news_negative = 0
            
            for word in words:
                if word in self.positive_words:
                    news_positive += 1
                elif word in self.negative_words:
                    news_negative += 1
            
            # 计算单条新闻情绪分数
            if news_positive > news_negative:
                score = min(1.0, 0.5 + news_positive * 0.1)
                positive_count += 1
            elif news_negative > news_positive:
                score = max(-1.0, -0.5 - news_negative * 0.1)
                negative_count += 1
            else:
                score = 0.0
            
            sentiment_scores.append(score)
        
        # 计算整体情绪
        if sentiment_scores:
            overall_sentiment = sum(sentiment_scores) / len(sentiment_scores)
        else:
            overall_sentiment = 0.0
        
        # 计算情绪分布
        positive_ratio = positive_count / total_news if total_news > 0 else 0
        negative_ratio = negative_count / total_news if total_news > 0 else 0
        neutral_ratio = 1 - positive_ratio - negative_ratio
        
        return {
            "overall_sentiment": overall_sentiment,
            "sentiment_label": self._get_sentiment_label(overall_sentiment),
            "positive_ratio": positive_ratio,
            "negative_ratio": negative_ratio,
            "neutral_ratio": neutral_ratio,
            "total_news": total_news,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "sentiment_trend": "上升" if overall_sentiment > 0.1 else "下降" if overall_sentiment < -0.1 else "平稳",
            "confidence": min(0.9, 0.5 + total_news * 0.05),
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_sentiment_label(self, score: float) -> str:
        """获取情绪标签"""
        if score > 0.3:
            return "极度乐观"
        elif score > 0.1:
            return "乐观"
        elif score > -0.1:
            return "中性"
        elif score > -0.3:
            return "悲观"
        else:
            return "极度悲观"
    
    def _get_default_sentiment(self) -> Dict[str, Any]:
        """获取默认情绪数据"""
        return {
            "overall_sentiment": 0.0,
            "sentiment_label": "中性",
            "positive_ratio": 0.33,
            "negative_ratio": 0.33,
            "neutral_ratio": 0.34,
            "total_news": 0,
            "positive_count": 0,
            "negative_count": 0,
            "sentiment_trend": "平稳",
            "confidence": 0.5,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_market_sentiment_indicators(self) -> Dict[str, Any]:
        """获取市场情绪指标"""
        try:
            # 获取多个维度的情绪数据
            news_sentiment = self.get_news_sentiment()
            
            # 这里可以添加其他情绪指标
            # 如社交媒体情绪、投资者情绪指数等
            
            return {
                "news_sentiment": news_sentiment,
                "social_sentiment": self._get_social_sentiment(),
                "investor_sentiment": self._get_investor_sentiment(),
                "overall_market_sentiment": self._calculate_overall_sentiment(news_sentiment),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ 获取市场情绪指标失败: {e}")
            return self._get_default_market_sentiment()
    
    def _get_social_sentiment(self) -> Dict[str, Any]:
        """获取社交媒体情绪（模拟）"""
        return {
            "platform": "微博/雪球",
            "sentiment_score": 0.2,
            "mention_count": 1500,
            "positive_ratio": 0.45,
            "negative_ratio": 0.25,
            "neutral_ratio": 0.30
        }
    
    def _get_investor_sentiment(self) -> Dict[str, Any]:
        """获取投资者情绪（模拟）"""
        return {
            "confidence_index": 65.5,
            "risk_appetite": "中等",
            "position_ratio": 0.72,
            "sentiment_score": 0.15
        }
    
    def _calculate_overall_sentiment(self, news_sentiment: Dict) -> float:
        """计算综合市场情绪"""
        news_score = news_sentiment.get("overall_sentiment", 0.0)
        social_score = 0.2  # 模拟社交媒体情绪
        investor_score = 0.15  # 模拟投资者情绪
        
        # 加权平均
        overall = (news_score * 0.5 + social_score * 0.3 + investor_score * 0.2)
        return round(overall, 3)
    
    def _get_default_market_sentiment(self) -> Dict[str, Any]:
        """获取默认市场情绪"""
        return {
            "news_sentiment": self._get_default_sentiment(),
            "social_sentiment": self._get_social_sentiment(),
            "investor_sentiment": self._get_investor_sentiment(),
            "overall_market_sentiment": 0.0,
            "timestamp": datetime.now().isoformat()
        }

# 创建实例
news_sentiment_analyzer = NewsSentimentAnalyzer()
