from datetime import datetime, timedelta

from flask_services.market_sentiment_service import MarketSentimentService


class DummyDataService:
    def get_stocks(self, limit=0):
        return {"data": {"stocks": [{"change_percent": 1.0}]}}


def test_parse_news_timestamp_from_unix_string():
    service = MarketSentimentService(DummyDataService())
    ts = int(datetime(2026, 5, 25, 22, 20, 12).timestamp())
    display, parsed = service._parse_news_timestamp(str(ts))
    assert parsed == float(ts)
    assert display.startswith("2026-05-25")


def test_parse_news_timestamp_from_datetime_text():
    service = MarketSentimentService(DummyDataService())
    display, parsed = service._parse_news_timestamp("2026-05-25 22:20:12")
    assert parsed > 0
    assert display == "2026-05-25 22:20:12"


def test_filter_and_sort_news_prefers_recent_items():
    service = MarketSentimentService(DummyDataService())
    now = datetime.now().timestamp()
    old = now - 10 * 24 * 3600
    items = [
        {"title": "old", "timestamp": old, "is_clickable": True},
        {"title": "new", "timestamp": now - 3600, "is_clickable": True},
    ]
    ranked = service._filter_and_sort_news(items, limit=5)
    assert ranked[0]["title"] == "new"
    assert all(item["title"] != "old" for item in ranked)
