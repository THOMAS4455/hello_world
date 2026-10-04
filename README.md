# 股票预测系统（Stock Prediction System）

[English](README_EN.md) | **简体中文**

面向 **A 股** 的本地研究/预测平台：FastAPI 后端 + React 前端。
具备完整闭环：数据 → 特征 → 预测 → 回测 → 选股 → 风控 → 模拟盘。

> **定位（先说局限）**：这是一个**能诚实评估策略、能控风险的研究工具**，
> **不是**能稳定盈利的选股系统。当前未找到可测出的稳健 alpha，
> 详见 **[系统能力报告](docs/SYSTEM_CAPABILITY_REPORT.md)**。

## 当前实测状态（2026-10-04）

下表数字全部由本仓库代码**实际运行**得出，不是设计目标。

| 项目 | 实测值 |
|---|---|
| `prepare_features()` 实际产出特征数 | **58 个**（22 基础 + 8 时序 + 13 交叉 + 15 微观结构） |
| 实际训练模型数 | 默认 **5 个**（RandomForest / GradientBoosting / ExtraTrees / LogisticRegression / SVM）；LightGBM / XGBoost / CatBoost 仅在装了可选依赖时才加入 |
| 相对「多数类基线」的预测 edge | **未证实** —— 34 条历史回测的 `improvement` 中位数为 **0.0000**（仅 7/34 为正，最大 +1.89pp） |
| 为什么这里的「准确率」会骗人 | 标签定义为 `1 = 未来 5 日涨幅 > +2%`，60%~90% 的样本为 0，因此「永远猜不会涨」的常量预测器本身就能拿 71% |
| 多标的消融（5 只股票 / 1,767 行样本外） | 所有变体**最大 edge 仅 +0.56pp**，三层集成在 3/5 标的上为负 |

**权威状态报告**：[docs/SYSTEM_CAPABILITY_REPORT.md](docs/SYSTEM_CAPABILITY_REPORT.md)（含完整消融证据）。

历史文档中「准确率 79.93% / F1 0.7102」等结论**不可复现**：其数据脚本依赖不存在的 `get_db_session`，
异常被静默吞掉后回退到 `np.random.seed(42)` 合成数据。这类文档已移入 [docs/archive/](docs/archive/) 并标注作废。

## 如何诚实地衡量性能

本项目唯一的结论指标是 **edge = 准确率 − 多数类基线**，且必须同时给出样本量 n 与 Wilson 区间。
已结算信号少于 200 条时，报告只输出「样本不足」，**不给出任何提升结论**。

```bash
# 抓行情 → 结算到期信号 → 重写实盘报告（幂等，可重复运行）
python scripts/daily_live_validation.py

# 消融：在同一组 purged walk-forward 折上比较各变体（edge vs 基线）
python scripts/ablation_edge.py --all-symbols --folds 3

# 死代码审计（CI 中非阻塞运行）
python scripts/audit_imports.py --report
```

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.9+、FastAPI、Uvicorn |
| 数据 | AKShare（前复权日线）、SQLite / JSON |
| 机器学习 | scikit-learn；LightGBM / XGBoost（可选，缺失时自动降级） |
| 前端 | React 18、Redux Toolkit、React Router、Plotly |
| 调度 | APScheduler（每工作日 16:45 实盘验证） |

## 快速开始

### 1. 后端

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS / Linux
.venv/Scripts/python app.py
```

后端启动于 `http://127.0.0.1:8000`，接口文档见 `http://127.0.0.1:8000/docs`。

### 2. 前端

```bash
cd frontend
npm ci
npm start          # http://localhost:3000
```

前端通过 `REACT_APP_API_BASE_URL` 指定后端地址，未设置时默认 `http://localhost:8000`。

### 3. Windows 一键启动

- `scripts/start_project.ps1`：后台启动前后端，日志写入 `logs/backend`、`logs/frontend`
- `scripts/start_bachelor_project.py`
- `start.bat`

### 4. 每日实盘验证（可选）

服务运行时由 APScheduler 自动触发。若不想依赖服务常驻，可注册 Windows 任务计划（**需你自行执行**）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/register_daily_task.ps1
```

## 目录结构

```text
.
|-- api/               HTTP 路由层
|-- flask_services/    服务层（目录名为历史遗留，实际不依赖 Flask）
|-- src/core/          预测器与数据采集
|-- src/validation/    信号追踪、结算、绩效报告、防过拟合统计
|-- src/trading/       交易约束、模拟盘
|-- src/portfolio/     组合与风险引擎
|-- src/research/      因子、选股决策
|-- src/jobs/          定时任务
|-- frontend/          React 前端
|-- scripts/           运维与评估脚本
|-- tests/             测试（pytest）
|-- docs/              文档（含 docs/archive/ 作废归档）
`-- data/              运行时数据（不入版本库）
```

## 主要接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| GET | `/api/stocks` | 股票列表 |
| GET | `/api/stocks/{symbol}` | 个股详情 |
| GET | `/api/stocks/realtime` | 实时行情 |
| GET | `/api/stocks/market-overview` | 市场概览 |
| GET | `/api/predictions/predict` | 单股方向预测 |
| POST | `/api/predictions/backtest` | 回测 |
| POST | `/api/auth/register`、`/api/auth/login` | 注册 / 登录 |
| GET / PUT | `/api/investment/watchlist` | 自选股 |
| POST | `/api/investment/portfolio/backtest` | 组合回测 |
| **GET** | **`/api/investment/live-performance`** | **实盘绩效（edge vs 基线 + 样本判定）** |
| GET / POST | `/api/investment/paper/account` | 模拟盘 |
| GET | `/api/tasks/status` | 任务状态 |

## 测试与 CI

```bash
.venv/Scripts/python -m pytest tests -q          # 101 passed, 1 xfailed
cd frontend && npm ci && npm run build
```

[.github/workflows/ci.yml](.github/workflows/ci.yml) 在每次推送/PR 执行三个 job：
后端全量测试（按 `requirements.txt` 锁定依赖）、前端 `npm ci && npm run build`、
Python 语法编译 + 死代码审计。

## 已知局限（均未解决）

1. **无稳健 alpha**：ML 方向预测、动量因子、GBDT+Alpha158 三条路径均未跑赢多数类基线（见消融表）。
2. **实盘样本不足**：当前仅 15 条已结算信号，报告标记 `insufficient_n = true`。
3. **幸存者偏差**：只覆盖当前存活股票，未并入退市名单，正收益结论需打折，详见 [docs/SURVIVORSHIP_BIAS.md](docs/SURVIVORSHIP_BIAS.md)。
4. **日线粒度**：无分钟/盘口数据，无法做日内。
5. **A 股做空受限**：只能做多，多空对冲收益不可实现。

## 安全

- **不要把密钥提交进版本库**。`docker-compose.yml` 使用 `${DEEPSEEK_API_KEY}` 等环境变量占位，实际值放在 `.env`（已 gitignore）。
- `data/users.json` 含账号密码哈希；`data/`、`logs/`、`.venv/`、`frontend/build/` 均已排除在版本控制之外。
- 一旦密钥曾进入 git 历史，请**轮换该密钥**：清除历史并不能让它重新变安全。

## 免责声明

本项目仅用于研究与学习，任何输出都不构成投资建议。
