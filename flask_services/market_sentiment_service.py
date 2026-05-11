"""
Market sentiment service based on real market data and online finance news.
No mock data is used.
"""

from __future__ import annotations

import math
import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests


class MarketSentimentService:
    def __init__(self, data_service: Any) -> None:
        self.data_service = data_service
        self.request_timeout = 12
        self.positive_words = {
            "上涨",
            "反弹",
            "走强",
            "利好",
            "回暖",
            "新高",
            "突破",
            "增持",
            "增长",
            "修复",
            "企稳",
            "改善",
        }
        self.negative_words = {
            "下跌",
            "走弱",
            "利空",
            "回落",
            "新低",
            "跌破",
            "减持",
            "下滑",
            "风险",
            "承压",
            "波动",
            "担忧",
        }
        self.finance_keywords = {
            "a股",
            "港股",
            "美股",
            "股",
            "股票",
            "股市",
            "市场",
            "指数",
            "基金",
            "债",
            "债券",
            "期货",
            "黄金",
            "原油",
            "汇率",
            "人民币",
            "美元",
            "利率",
            "降息",
            "加息",
            "通胀",
            "经济",
            "金融",
            "银行",
            "证券",
            "保险",
            "公司",
            "业绩",
            "财报",
            "营收",
            "利润",
            "并购",
            "融资",
            "ipo",
            "芯片",
            "新能源",
            "地产",
            "消费",
            "制造",
            "科技",
            "央行",
            "政策",
        }

    @staticmethod
    def _clamp(value: float, min_value: float = -1.0, max_value: float = 1.0) -> float:
        return max(min_value, min(max_value, value))

    @staticmethod
    def _score_to_label(score: float) -> str:
        if score >= 0.35:
            return "乐观"
        if score >= 0.1:
            return "偏乐观"
        if score <= -0.35:
            return "悲观"
        if score <= -0.1:
            return "偏谨慎"
        return "中性"

    @staticmethod
    def _first_present(row: Dict[str, Any], *keys: str, default: Any = "") -> Any:
        for key in keys:
            if key in row and row.get(key) not in (None, ""):
                return row.get(key)
        return default

    def _is_finance_relevant(self, title: str) -> bool:
        text = str(title or "").strip().lower()
        if not text:
            return False
        return any(keyword in text for keyword in self.finance_keywords)

    def _normalize_news_item(
        self,
        *,
        title: str,
        url: str = "",
        source: str = "",
        time_text: Any = "",
    ) -> Optional[Dict[str, Any]]:
        title = str(title or "").strip()
        if not title:
            return None
        url = str(url or "").strip()
        source = str(source or "unknown").strip().lower() or "unknown"
        if url and not url.startswith(("http://", "https://")):
            url = ""
        return {
            "title": title,
            "url": url,
            "source": source,
            "time": str(time_text or "").strip(),
            "is_clickable": bool(url),
        }

    def _extract_stocks(self) -> List[Dict[str, Any]]:
        payload = self.data_service.get_stocks(limit=0)
        stocks = payload.get("data", {}).get("stocks", []) if isinstance(payload, dict) else payload
        if not isinstance(stocks, list) or not stocks:
            raise Exception("No real-time stock universe data available")
        return stocks

    def _compute_market_metrics(self, stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        changes = []
        rising = 0
        falling = 0
        flat = 0
        strong_up = 0
        strong_down = 0

        for stock in stocks:
            change_pct = float(stock.get("change_percent", 0.0) or 0.0)
            changes.append(change_pct)
            if change_pct > 0:
                rising += 1
            elif change_pct < 0:
                falling += 1
            else:
                flat += 1
            if change_pct >= 2.0:
                strong_up += 1
            if change_pct <= -2.0:
                strong_down += 1

        total = len(changes)
        avg_change_pct = statistics.fmean(changes)
        median_change_pct = statistics.median(changes)
        volatility_pct = statistics.pstdev(changes) if total > 1 else 0.0

        breadth_score = (rising - falling) / total
        change_score = self._clamp(avg_change_pct / 3.0)
        momentum_score = (strong_up - strong_down) / total
        market_score = self._clamp(0.55 * breadth_score + 0.30 * change_score + 0.15 * momentum_score)

        return {
            "score": round(market_score, 4),
            "label": self._score_to_label(market_score),
            "total_stocks": total,
            "rising_count": rising,
            "falling_count": falling,
            "flat_count": flat,
            "rising_ratio": round(rising / total, 4),
            "falling_ratio": round(falling / total, 4),
            "avg_change_percent": round(avg_change_pct, 4),
            "median_change_percent": round(median_change_pct, 4),
            "volatility_percent": round(volatility_pct, 4),
            "strong_up_ratio": round(strong_up / total, 4),
            "strong_down_ratio": round(strong_down / total, 4),
        }

    def _fetch_sina_finance_news_paged(
        self, limit: int = 20, keyword: Optional[str] = None, max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        url = "https://feed.mix.sina.com.cn/api/roll/get"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        }

        hard_limit = max(20, min(int(limit or 20), 400))
        page_size = 50
        pages = min(max_pages or max(1, math.ceil(hard_limit / page_size)), 10)

        news: List[Dict[str, Any]] = []
        seen = set()
        for page in range(1, pages + 1):
            params = {
                "pageid": "153",
                "lid": "2510",
                "k": keyword or "",
                "num": page_size,
                "page": str(page),
                "r": str(datetime.now().timestamp()),
            }
            last_err: Optional[str] = None
            payload = {}
            for _ in range(3):
                try:
                    resp = requests.get(url, params=params, headers=headers, timeout=self.request_timeout)
                    if resp.status_code != 200:
                        last_err = f"Sina news request failed: {resp.status_code}"
                        continue
                    payload = resp.json()
                    last_err = None
                    break
                except Exception as exc:
                    last_err = str(exc)
            if last_err is not None:
                raise Exception(last_err)

            items = payload.get("result", {}).get("data", [])
            for item in items:
                news_item = self._normalize_news_item(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    source="sina",
                    time_text=item.get("ctime"),
                )
                if not news_item:
                    continue
                key = news_item["title"].lower()
                if key in seen:
                    continue
                seen.add(key)
                news.append(news_item)
            if len(news) >= hard_limit:
                break
        return news

    def _fetch_akshare_finance_news(self, limit: int = 20) -> List[Dict[str, Any]]:
        import akshare as ak

        df = ak.stock_info_global_em()
        if df is None or df.empty:
            raise Exception("AKShare global news is empty")

        news: List[Dict[str, Any]] = []
        for _, row in df.head(max(10, min(limit * 3, 120))).iterrows():
            row_dict = row.to_dict()
            title = self._first_present(row_dict, "标题", "鏍囬")
            if not self._is_finance_relevant(str(title)):
                continue
            source = self._first_present(row_dict, "来源", "鏉ユ簮", default="eastmoney")
            time_text = self._first_present(row_dict, "发布时间", "发布时间", "鍙戝竷鏃堕棿")
            url = self._first_present(row_dict, "链接", "资讯链接", "url", "URL")
            news_item = self._normalize_news_item(
                title=title,
                url=url,
                source=source,
                time_text=time_text,
            )
            if news_item:
                news.append(news_item)
            if len(news) >= limit:
                break
        return news

    def _fetch_finance_news(
        self,
        limit: int = 20,
        sources: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        errors: List[str] = []
        merged: List[Dict[str, Any]] = []
        seen = set()
        source_set = set(sources or ["sina", "akshare"])

        fetchers: List[tuple[str, Any]] = []
        if "sina" in source_set:
            fetchers.append(("sina", lambda limit: self._fetch_sina_finance_news_paged(limit=limit, keyword=None)))
        if "akshare" in source_set:
            fetchers.append(("akshare", self._fetch_akshare_finance_news))
        if not fetchers:
            raise Exception("No available news sources configured")

        for source_name, fetcher in fetchers:
            try:
                rows = fetcher(limit=limit)
                if not rows:
                    errors.append(f"{source_name}: empty result")
                    continue
                for item in rows:
                    title = str(item.get("title", "")).strip()
                    if not title:
                        continue
                    key = title.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    merged.append(item)
            except Exception as exc:
                err_text = str(exc).strip() or "unknown error"
                errors.append(f"{source_name}: {err_text}")

        if not merged:
            detail = " | ".join(errors) if errors else "all configured sources returned no usable news"
            raise Exception("Failed to fetch online finance news: " + detail)

        merged.sort(key=lambda item: (0 if item.get("is_clickable") else 1, item.get("time", "")))
        return merged[:limit]

    def _compute_news_sentiment(self, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not news_items:
            raise Exception("No finance news to analyze sentiment")

        positive = 0
        negative = 0
        neutral = 0
        sentiment_sum = 0.0

        for item in news_items:
            title = str(item.get("title", ""))
            pos_hits = sum(1 for word in self.positive_words if word in title)
            neg_hits = sum(1 for word in self.negative_words if word in title)
            total_hits = pos_hits + neg_hits
            if total_hits == 0:
                neutral += 1
                continue
            score = (pos_hits - neg_hits) / total_hits
            sentiment_sum += score
            if score > 0:
                positive += 1
            elif score < 0:
                negative += 1
            else:
                neutral += 1

        count = len(news_items)
        avg_score = sentiment_sum / count
        news_score = self._clamp(avg_score)
        return {
            "score": round(news_score, 4),
            "label": self._score_to_label(news_score),
            "total_news": count,
            "positive_count": positive,
            "negative_count": negative,
            "neutral_count": neutral,
            "positive_ratio": round(positive / count, 4),
            "negative_ratio": round(negative / count, 4),
            "neutral_ratio": round(neutral / count, 4),
        }

    def _compute_stock_context(self, symbol: str) -> Dict[str, Any]:
        detail = self.data_service.get_stock_detail(symbol)
        history = detail.get("history") or []
        if not history:
            raise Exception(f"No historical data for {symbol}")

        closes = []
        for row in history:
            close = row.get("close")
            if close is None:
                continue
            try:
                closes.append(float(close))
            except Exception:
                continue

        if len(closes) < 5:
            raise Exception(f"Insufficient history for {symbol}: {len(closes)} rows")

        latest = closes[-1]
        ma5 = statistics.fmean(closes[-5:])
        ma20 = statistics.fmean(closes[-20:]) if len(closes) >= 20 else ma5
        momentum5 = (latest - closes[-5]) / closes[-5] if closes[-5] != 0 else 0.0
        trend_score = self._clamp(0.6 * ((latest - ma5) / ma5 if ma5 else 0.0) + 0.4 * momentum5)
        return {
            "symbol": symbol,
            "name": detail.get("name", symbol),
            "price": round(float(detail.get("current_price", detail.get("price", latest)) or latest), 4),
            "change_percent": round(float(detail.get("change_percent", 0.0) or 0.0), 4),
            "trend_score": round(trend_score, 4),
            "ma5": round(ma5, 4),
            "ma20": round(ma20, 4),
            "momentum_5d": round(momentum5, 4),
            "history_points": len(closes),
        }

    def _build_ai_prompt(
        self,
        market_metrics: Dict[str, Any],
        news_metrics: Dict[str, Any],
        final_score: float,
        label: str,
        news_items: List[Dict[str, Any]],
        stock_context: Optional[Dict[str, Any]],
        keyword: Optional[str],
        sources: List[str],
    ) -> str:
        headlines_text = "\n".join(
            f"- [{item.get('source') or 'unknown'}] {item.get('title') or ''}" for item in news_items[:24]
        )

        stock_text = ""
        if stock_context:
            stock_text = (
                "\n个股上下文\n"
                f"- 股票: {stock_context['symbol']} {stock_context.get('name', '')}\n"
                f"- 最新价: {stock_context['price']}\n"
                f"- 当日涨跌幅: {stock_context['change_percent']}%\n"
                f"- 5日动量: {stock_context['momentum_5d']}\n"
                f"- 趋势得分: {stock_context['trend_score']}\n"
            )

        return (
            "请基于以下真实数据给出市场情绪分析。要求：使用中文自然段输出，不要使用编号列表。"
            "先给结论，再给依据，再给短中线建议，最后给风险提示。\n"
            f"综合情绪分数: {round(final_score, 4)}\n"
            f"综合情绪标签: {label}\n"
            f"抓取新闻来源: {','.join(sources)}\n"
            f"定向关键词: {keyword or '无'}\n"
            f"市场广度: 上涨{market_metrics['rising_count']} / 下跌{market_metrics['falling_count']} / 平盘{market_metrics['flat_count']}\n"
            f"上涨占比: {market_metrics['rising_ratio']}\n"
            f"平均涨跌幅: {market_metrics['avg_change_percent']}%\n"
            f"横截面波动率: {market_metrics['volatility_percent']}%\n"
            f"新闻情绪分数: {news_metrics['score']}\n"
            f"新闻统计: 正面{news_metrics['positive_count']} 负面{news_metrics['negative_count']} 中性{news_metrics['neutral_count']} 总计{news_metrics['total_news']}\n"
            f"{stock_text}\n"
            "最近财经新闻标题\n"
            f"{headlines_text}"
        )

    def build_market_sentiment(
        self,
        symbol: Optional[str] = None,
        news_limit: int = 120,
        keyword: Optional[str] = None,
        sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        stocks = self._extract_stocks()
        market_metrics = self._compute_market_metrics(stocks)

        stock_context = self._compute_stock_context(symbol) if symbol else None
        source_list = [s.strip().lower() for s in (sources or ["sina", "akshare"]) if str(s).strip()]
        if not source_list:
            source_list = ["sina", "akshare"]

        final_keyword = (keyword or "").strip()
        all_news_items = self._fetch_finance_news(
            limit=max(20, min(int(news_limit or 120), 400)),
            sources=source_list,
        )
        target_match_count = 0
        if final_keyword:
            kw = final_keyword.lower()
            targeted = [item for item in all_news_items if kw in str(item.get("title", "")).lower()]
            target_match_count = len(targeted)
            news_items = targeted if targeted else all_news_items
        else:
            news_items = all_news_items

        news_metrics = self._compute_news_sentiment(news_items)
        market_score = float(market_metrics["score"])
        news_score = float(news_metrics["score"])
        final_score = (
            self._clamp(0.5 * market_score + 0.25 * news_score + 0.25 * float(stock_context["trend_score"]))
            if stock_context
            else self._clamp(0.7 * market_score + 0.3 * news_score)
        )

        label = self._score_to_label(final_score)
        confidence = self._clamp(
            0.45
            + min(0.25, len(stocks) / 30000)
            + min(0.20, news_metrics["total_news"] / 120)
            + min(0.10, abs(final_score) / 2),
            0.0,
            0.95,
        )

        factors = [
            {
                "name": "市场广度",
                "value": round(market_metrics["rising_ratio"] - market_metrics["falling_ratio"], 4),
                "description": f"上涨占比 {market_metrics['rising_ratio']}，下跌占比 {market_metrics['falling_ratio']}",
            },
            {
                "name": "平均涨跌幅",
                "value": market_metrics["avg_change_percent"],
                "description": "全市场个股当日涨跌幅均值",
            },
            {
                "name": "新闻情绪",
                "value": news_metrics["score"],
                "description": f"基于 {news_metrics['total_news']} 条实时财经新闻标题统计",
            },
        ]
        if stock_context:
            factors.append(
                {
                    "name": "个股趋势",
                    "value": stock_context["trend_score"],
                    "description": f"{stock_context['symbol']} 5日动量 {stock_context['momentum_5d']}",
                }
            )

        return {
            "score": round(final_score, 4),
            "label": label,
            "confidence": round(confidence, 4),
            "scope": "market+stock" if stock_context else "market",
            "symbol": symbol or "",
            "market_metrics": market_metrics,
            "news_metrics": news_metrics,
            "news_items": news_items,
            "crawl_config": {
                "news_limit": max(20, min(int(news_limit or 120), 400)),
                "keyword": final_keyword,
                "sources": source_list,
                "target_match_count": target_match_count,
            },
            "stock_context": stock_context,
            "factors": factors,
            "ai_prompt": self._build_ai_prompt(
                market_metrics=market_metrics,
                news_metrics=news_metrics,
                final_score=final_score,
                label=label,
                news_items=news_items,
                stock_context=stock_context,
                keyword=final_keyword or None,
                sources=source_list,
            ),
            "timestamp": datetime.now().isoformat(),
        }
