# 投资平台 MVP 说明

## 概述

投资平台 MVP 将系统从「单股预测工具」升级为「以用户组合为中心的投资工作台」，前端入口为 `/investment` 投资中心。

## 用户流程

1. **登录** — 所有投资 API 需 Bearer Token。
2. **维护自选池** — 在投资中心「组合」Tab 添加 5–20 只股票。
3. **组合回测** — 选择权重模式（等权 / 信号加权），运行回测，查看组合权益曲线 vs 等权买入持有。
4. **模拟盘** — 创建虚拟账户，手动「推进一日」，查看持仓、权益曲线与成交明细。
5. **洞察** — 查看每日智能简报：自选池信号摘要、风险提醒、模拟盘变动。
6. **信号验证** — 预测页或投资中心可查看单股历史信号准确率与平均收益。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/investment/watchlist` | 获取自选池与配置 |
| PUT | `/api/investment/watchlist` | 更新自选池 |
| GET | `/api/investment/config` | 获取组合配置 |
| PUT | `/api/investment/config` | 更新组合配置 |
| POST | `/api/investment/portfolio/backtest` | 运行组合回测 |
| GET | `/api/investment/paper/account` | 获取模拟账户 |
| POST | `/api/investment/paper/account` | 创建模拟账户 |
| POST | `/api/investment/paper/advance-day` | 推进一个交易日 |
| GET | `/api/investment/paper/equity-curve` | 权益曲线 |
| GET | `/api/investment/paper/trades` | 成交明细 |
| GET | `/api/investment/signal-stats/{symbol}` | 信号历史统计 |
| GET | `/api/investment/daily-brief` | 每日智能简报 |

## 数据文件

- `data/user_investments.json` — 用户自选池与组合配置
- `data/paper_accounts.json` — 模拟账户状态
- `data/signal_logs.json` — 全局信号追踪日志

## 模拟盘规则（MVP 简化）

- 仅做多 + 空仓
- 佣金 0.1%
- 100 股整数倍
- **未实现** T+1、涨跌停（UI 已标注「简化模拟」）

## 二期预留

- T+1 / 涨跌停约束
- 每日自动推进模拟盘
- PostgreSQL 替代 JSON 存储
- Meta-Labeling 第二层可信度

## 测试

```bash
pytest tests/test_signal_tracker.py tests/test_investment_watchlist.py tests/test_portfolio_engine.py tests/test_paper_account.py tests/test_api/test_investment_api.py -q
```
