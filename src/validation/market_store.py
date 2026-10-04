"""Local daily-bar store shared by live signal validation and model ablation.

The project previously had no usable price store: the "real data" scripts
imported a non-existent get_db_session helper and silently fell back to
synthetic random walks. This module is the single source of truth for
historical bars.

Design rules (deliberate):

* SQLite, one file, data/market.sqlite (git-ignored).
* Idempotent writes: INSERT ... ON CONFLICT DO UPDATE, so re-running the daily
  job never duplicates rows.
* Loud failures: a frame missing a required column raises instead of being
  silently coerced or replaced with synthetic data.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "market.sqlite"

REQUIRED_COLUMNS = ("date", "close_price")
OPTIONAL_NUMERIC = ("open_price", "high_price", "low_price", "volume")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_bars (
    symbol      TEXT NOT NULL,
    date        TEXT NOT NULL,
    open_price  REAL,
    high_price  REAL,
    low_price   REAL,
    close_price REAL,
    volume      REAL,
    adj         TEXT DEFAULT 'qfq',
    source      TEXT,
    fetched_at  REAL,
    PRIMARY KEY (symbol, date)
);
CREATE INDEX IF NOT EXISTS idx_daily_bars_symbol_date
    ON daily_bars (symbol, date);
"""


class MarketStore:
    """Thread-safe wrapper around the local daily-bar SQLite database."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    # ------------------------------------------------------------------ setup
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(_SCHEMA)

    # ------------------------------------------------------------------ write
    @staticmethod
    def validate_frame(df: pd.DataFrame) -> None:
        """Raise ValueError when the frame cannot be stored honestly."""
        if df is None or len(df) == 0:
            raise ValueError("empty frame: refusing to write")
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                "missing required column(s) %s; got %s" % (missing, list(df.columns))
            )

    def upsert_bars(
        self,
        symbol: str,
        df: pd.DataFrame,
        *,
        adj: str = "qfq",
        source: str = "akshare",
    ) -> int:
        """Insert or update bars for symbol; returns the number of rows written."""
        self.validate_frame(df)
        symbol = str(symbol).strip()
        if not symbol:
            raise ValueError("empty symbol")

        work = df.copy()
        work["date"] = pd.to_datetime(work["date"], errors="coerce")
        work = work.dropna(subset=["date", "close_price"])
        if work.empty:
            raise ValueError("no rows with a parsable date and close_price")
        work = work.sort_values("date")
        work["date"] = work["date"].dt.strftime("%Y-%m-%d")

        fetched_at = time.time()
        rows = []
        for _, r in work.iterrows():
            rows.append(
                (
                    symbol,
                    r["date"],
                    _as_float(r, "open_price"),
                    _as_float(r, "high_price"),
                    _as_float(r, "low_price"),
                    float(r["close_price"]),
                    _as_float(r, "volume"),
                    adj,
                    source,
                    fetched_at,
                )
            )

        sql = """
        INSERT INTO daily_bars
            (symbol, date, open_price, high_price, low_price, close_price,
             volume, adj, source, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol, date) DO UPDATE SET
            open_price  = excluded.open_price,
            high_price  = excluded.high_price,
            low_price   = excluded.low_price,
            close_price = excluded.close_price,
            volume      = excluded.volume,
            adj         = excluded.adj,
            source      = excluded.source,
            fetched_at  = excluded.fetched_at
        """
        with self._lock, self._connect() as conn:
            conn.executemany(sql, rows)
        return len(rows)

    # ------------------------------------------------------------------- read
    def load_bars(self, symbol: str, limit: Optional[int] = None) -> pd.DataFrame:
        """Return bars for symbol ascending by date (empty frame if unknown)."""
        symbol = str(symbol).strip()
        sql = (
            "SELECT date, open_price, high_price, low_price, close_price, volume "
            "FROM daily_bars WHERE symbol = ? ORDER BY date"
        )
        with self._lock, self._connect() as conn:
            df = pd.read_sql_query(sql, conn, params=(symbol,))
        if limit is not None and len(df) > limit:
            df = df.tail(int(limit)).reset_index(drop=True)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df

    def bar_count(self, symbol: str) -> int:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM daily_bars WHERE symbol = ?",
                (str(symbol).strip(),),
            )
            return int(cur.fetchone()[0])

    def symbols(self):
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "SELECT DISTINCT symbol FROM daily_bars ORDER BY symbol"
            )
            return [row[0] for row in cur.fetchall()]

    def coverage(self) -> Dict[str, Any]:
        """Full-population coverage summary over every stored symbol."""
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "SELECT COUNT(DISTINCT symbol), COUNT(*), MIN(date), MAX(date) "
                "FROM daily_bars"
            )
            n_symbols, n_rows, first_date, last_date = cur.fetchone()
        return {
            "db_path": str(self.path),
            "symbols": int(n_symbols or 0),
            "rows": int(n_rows or 0),
            "first_date": first_date,
            "last_date": last_date,
        }

    def missing_forward_bars(self, symbol: str, entry_date: str, horizon: int) -> bool:
        """True when there are not yet horizon bars strictly after entry_date."""
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM daily_bars WHERE symbol = ? AND date > ?",
                (str(symbol).strip(), str(entry_date)),
            )
            return int(cur.fetchone()[0]) < int(horizon)


def _as_float(row: pd.Series, column: str) -> Optional[float]:
    if column not in row or pd.isna(row[column]):
        return None
    try:
        return float(row[column])
    except (TypeError, ValueError):
        return None


def load_bars_as_history(store: MarketStore, symbol: str) -> pd.DataFrame:
    """Adapter for OutcomeResolver, which expects a price frame keyed by date."""
    df = store.load_bars(symbol)
    if df.empty:
        raise ValueError("no local bars for symbol %s" % symbol)
    return df
