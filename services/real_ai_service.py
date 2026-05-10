"""
Real DeepSeek AI service with normalized prompt and response format.
"""

import re
import time
from pathlib import Path
from typing import Any, Dict
import sys

import requests

# Ensure config package is importable when executed from project root.
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "config"))

from ai_config import (  # noqa: E402
    AI_TIMEOUT,
    DEFAULT_MODEL,
    DEEPSEEK_API_KEY,
    DEEPSEEK_API_URL,
    MAX_TOKENS,
    RETRY_COUNT,
    RETRY_DELAY,
    TEMPERATURE,
)


class RealAIService:
    """DeepSeek AI wrapper for stock analysis."""

    def __init__(self) -> None:
        self.api_key = DEEPSEEK_API_KEY
        self.api_url = DEEPSEEK_API_URL
        self.model = DEFAULT_MODEL
        self.max_tokens = MAX_TOKENS
        self.temperature = TEMPERATURE
        self.timeout = AI_TIMEOUT
        self.retry_count = RETRY_COUNT
        self.retry_delay = RETRY_DELAY
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timeout = 600  # 10 minutes

    def _build_system_prompt(self) -> str:
        return (
            "你是专业的A股投研助手。请用中文回答，并严格遵守以下规则：\n"
            "1) 先给结论，再给依据，不要堆砌空话。\n"
            "2) 没有实时数据时必须明确说明“基于通用分析，不是实时行情”，禁止编造具体实时价格。\n"
            "3) 不提供保证收益承诺，不给极端或绝对化表述。\n"
            "4) 输出必须是自然、连贯的语段，不要使用 Markdown 标题、井号、表格或代码块。\n"
            "5) 建议部分要覆盖短线、中线、长线三个维度。\n"
            "6) 风险提示至少包含三条具体风险点。\n"
            "7) 推荐使用如下自然段落顺序：先写结论段，再写依据段，再写建议段，再写风险与免责声明段。"
        )

    def analyze(self, query: str) -> str:
        cache_key = f"ai_analysis_{hash(query)}"
        if cache_key in self.cache:
            cache_time = self.cache[cache_key]["timestamp"]
            if time.time() - cache_time < self.cache_timeout:
                return self.cache[cache_key]["data"]

        response = self._call_deepseek_api(query)
        normalized = self._normalize_response(response)
        self.cache[cache_key] = {"timestamp": time.time(), "data": normalized}
        return normalized

    def _call_deepseek_api(self, query: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": query},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error = None
        for attempt in range(self.retry_count):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                last_error = Exception(
                    f"API call failed: {response.status_code} - {response.text}"
                )
            except requests.exceptions.RequestException as e:
                last_error = e

            if attempt < self.retry_count - 1:
                time.sleep(self.retry_delay)

        raise Exception(f"AI analysis failed: {last_error}")

    def _normalize_response(self, content: str) -> str:
        text = (content or "").replace("\r\n", "\n").strip()
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Remove markdown headings/symbols if the model returns them.
        text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
        text = re.sub(r"(?m)^\s*[-*]\s+", "", text)
        text = re.sub(r"(?m)^\s*\d+\)\s*", "", text)
        text = text.strip()

        # If already paragraph-style and long enough, return directly.
        if len(text) >= 120 and "#" not in text:
            return text

        # Fallback to paragraph-style output (no markdown marks).
        core = text or "当前信息不足，建议先补充标的、周期和策略偏好。"
        return (
            f"结论方面，{core}\n\n"
            "从依据来看，本次分析基于通用投研框架进行判断，重点参考行业景气度、估值水平、资金偏好和历史波动特征。"
            "如果没有接入实时行情，结论只能反映一般性研究观点，不等同于实时盘中判断。\n\n"
            "在操作上，短线建议以控制仓位和明确止损为主，避免追涨杀跌；中线建议跟踪基本面变化与业绩兑现情况，"
            "在估值合理区间分批布局；长线建议关注公司现金流质量、行业竞争格局和管理层执行力，保持分散配置。\n\n"
            "风险方面，需要重点关注宏观与政策扰动带来的市场波动风险、业绩不及预期导致的估值回撤风险，"
            "以及流动性收缩时的交易冲击风险。以上内容仅作为信息分析与研究参考，不构成任何投资建议，投资决策请结合自身风险承受能力谨慎判断。"
        )

    def get_service_status(self) -> Dict[str, Any]:
        try:
            _ = self._call_deepseek_api("请回复：服务正常")
            return {
                "status": "online",
                "service": "DeepSeek AI",
                "model": self.model,
                "api_key_status": "valid",
                "last_check": time.time(),
                "cache_size": len(self.cache),
            }
        except Exception as e:
            return {
                "status": "offline",
                "service": "DeepSeek AI",
                "error": str(e),
                "last_check": time.time(),
                "fallback_mode": True,
            }

    def clear_cache(self) -> bool:
        self.cache.clear()
        return True

    def get_runtime_config(self) -> Dict[str, Any]:
        masked = ""
        if self.api_key:
            if len(self.api_key) <= 8:
                masked = "*" * len(self.api_key)
            else:
                masked = f"{self.api_key[:4]}***{self.api_key[-4:]}"
        return {
            "api_url": self.api_url,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay,
            "api_key_masked": masked,
            "has_api_key": bool(self.api_key),
        }

    def update_runtime_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(config, dict):
            raise Exception("AI config payload must be an object")

        if "api_key" in config:
            api_key = str(config.get("api_key") or "").strip()
            if api_key:
                self.api_key = api_key

        if "api_url" in config:
            api_url = str(config.get("api_url") or "").strip()
            if api_url:
                self.api_url = api_url

        if "model" in config:
            model = str(config.get("model") or "").strip()
            if model:
                self.model = model

        if "max_tokens" in config:
            self.max_tokens = int(config.get("max_tokens") or self.max_tokens)

        if "temperature" in config:
            self.temperature = float(config.get("temperature") or self.temperature)

        if "timeout" in config:
            self.timeout = int(config.get("timeout") or self.timeout)

        if "retry_count" in config:
            self.retry_count = int(config.get("retry_count") or self.retry_count)

        if "retry_delay" in config:
            self.retry_delay = float(config.get("retry_delay") or self.retry_delay)

        self.clear_cache()
        return self.get_runtime_config()

    def get_cache_info(self) -> Dict[str, Any]:
        return {
            "cache_size": len(self.cache),
            "cache_timeout": self.cache_timeout,
            "oldest_cache": min(
                [item["timestamp"] for item in self.cache.values()],
                default=None,
            ),
            "newest_cache": max(
                [item["timestamp"] for item in self.cache.values()],
                default=None,
            ),
        }


real_ai_service = RealAIService()
