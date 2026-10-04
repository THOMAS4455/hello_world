# 文档索引

## 先读这个

- **[SYSTEM_CAPABILITY_REPORT.md](SYSTEM_CAPABILITY_REPORT.md)** — **权威状态报告**：系统能做什么、不能做什么，
  以及每一项结论背后的实测数据（含 2026-10-04 消融复核）。判断项目现状请以此为准。

## 使用与开发

- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** — 接口与用法示例
- **[DEVELOPMENT.md](DEVELOPMENT.md)** — 开发说明
- **[INVESTMENT_PLATFORM_V2.md](INVESTMENT_PLATFORM_V2.md)** / **[INVESTMENT_PLATFORM_MVP.md](INVESTMENT_PLATFORM_MVP.md)** — 投资研究模块
- **[SURVIVORSHIP_BIAS.md](SURVIVORSHIP_BIAS.md)** — 幸存者偏差说明（**未解决的已知局限**）

## 实盘验证（2026-10-04 新增）

命令行入口（在项目根目录执行）：

    python scripts/daily_live_validation.py                   # 抓行情 -> 结算信号 -> 写报告
    python scripts/ablation_edge.py --all-symbols --folds 3   # 消融：各变体 vs 多数类基线
    python scripts/audit_imports.py --report                  # 死代码审计

指标口径：**edge = accuracy − 多数类基线**（附 n 与 Wilson 区间）。样本 < 200 时报告只写「样本不足」，
不给任何提升结论。台账位于 data/live_eval/（不进版本库）。

## 归档：不可复现的性能声明

[docs/archive/](archive/) 存放 2026-10-04 复核判定为**不可复现**的历史文档（79.93% / F1 0.7102 等），
保留以备追溯，**不得**再作为成果引用。详见 [archive/README.md](archive/README.md)。

## 已删除的脚本（索引不再指向它们）

verify_models.py、verify_features.py、test_with_real_data.py、test_accuracy.py、init_database.py
等已于 2026-10-04 删除：它们依赖不存在的 get_db_session（且 sqlalchemy 未安装），
异常被静默吞掉后**回退到合成随机数据**，属于会误导结论的失效代码。

仍保留的脚本（见 scripts/）：daily_live_validation.py、ablation_edge.py、audit_imports.py、
run_backtest.py、backfill_feature_history.py、download_delisted.py、start_akshare_server.py、
start_bachelor_project.py、register_daily_task.ps1。
