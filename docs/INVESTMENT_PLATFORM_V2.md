# 投资平台 V2 说明

在 MVP 基础上，V2 引入信号结算闭环、TBM/Meta-Labeling、历史回放模拟盘、组合绩效指标与定时任务。

## Phase 1：MVP 缺口补齐

- `outcome_resolver.py`：按历史价格结算 `signal_logs` 的 `outcome_return`
- 预测成功后自动触发 lazy resolve
- 用户 `risk_level` 映射到 `min_confidence` / `max_position_pct` / `max_total_equity_pct`
- 投资中心洞察 Tab 展示 Meta 评分与历史准确率

## Phase 2：信号验证

- `triple_barrier.py`：三重屏障标签（上/下/时间）
- `meta_label_filter.py`：基于历史准确率 + 置信度的交易过滤
- 配置项 `label_mode`: `fixed_horizon` | `triple_barrier`

## Phase 3：模拟盘与组合分析

- 模拟盘按测试段历史交易日回放（`replay_cursor`）
- T+1 卖出限制、简化涨跌停（±9.5%）
- `portfolio_metrics.py`：Sharpe、回撤、胜率、盈亏比
- 组合回测响应含 `metrics` 字段

## Phase 4：平台化

- `src/jobs/investment_jobs.py`：每日 16:30 结算信号 + 可选自动推进模拟盘
- `investment_repository.py`：JSON 存储抽象，预留 PostgreSQL
- `scripts/verify_investment_flow.py`：E2E 冒烟脚本

## 新增配置项

| 键 | 说明 | 默认 |
|----|------|------|
| `label_mode` | 信号结算标签模式 | `fixed_horizon` |
| `auto_advance_paper` | 收盘后自动推进模拟盘 | `false` |
| `max_symbols` | 回测/模拟盘最大标的数 | `10` |

## API 增补

- `GET /api/investment/portfolio/report/{cache_key}` — 获取缓存的回测报告

## 测试

```bash
py -m pytest tests/test_outcome_resolver.py tests/test_triple_barrier.py tests/test_meta_label_filter.py tests/test_portfolio_metrics.py tests/test_signal_tracker.py tests/test_investment_watchlist.py tests/test_portfolio_engine.py tests/test_paper_account.py tests/test_api/test_investment_api.py -q
```

## 开源参考

- [Qlib](https://github.com/microsoft/qlib) — 组合分析工作流
- [bbca-tbm-meta](https://github.com/rayhantithokharisma/bbca-tbm-meta) — TBM 标签
- [hudson-and-thames/meta-labeling](https://github.com/hudson-and-thames/meta-labeling) — Meta-Labeling
- [VectorBT](https://github.com/polakowo/vectorbt) — 组合绩效指标
