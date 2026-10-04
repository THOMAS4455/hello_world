# 归档：不可复现的性能声明

本目录存放 2026-10-04 复核后判定为**不可复现**的历史文档，保留以备追溯，但**不得**再作为成果引用。

## 为什么归档

1. **数据来源断裂**：产生这些数字的脚本（scripts/test_accuracy.py、scripts/test_with_real_data.py、
   tests/test_with_real_data.py）调用 `config.database.get_db_session`，而该函数**不存在**，
   且 sqlalchemy 未安装。异常被 `except Exception` 静默捕获，回退到 `np.random.seed(42)`
   的合成随机游走。实测（2026-10-04）：直接运行即 ImportError，随后因 GBK 编码崩溃退出码 1。
2. **样本量极小**：REAL_DATA_test_results.csv 中各数值的最小分母为 19 / 38 / 76，即评测集只有几十条样本。
3. **文档互相矛盾**：本目录内同时存在 79.93%/F1 0.7102、65.8%/F1 0.580 两种口径，且 OPTIMIZATION_FINAL_SUMMARY.md
   列出「8 个模型准确率全部为 79.93%」——训练准确率 100% 而测试集所有模型同分，指向测试集预测塌缩为常量。
4. **与全量实测冲突**：对 data/prediction_runs.json 中 34 条历史回测做全量统计，
   `improvement`（模型准确率 − 多数类基线）中位数为 **0.0000**，仅 7/34 为正，最大值 +1.89 个百分点。

## 现在的权威口径

见 [docs/SYSTEM_CAPABILITY_REPORT.md](../SYSTEM_CAPABILITY_REPORT.md)（结论：无稳定 alpha）与
[data/live_eval/](../../data/live_eval/)（每日实盘验证 ledger，指标为 edge，而非准确率）。

## 文件清单

| 文件 | 原位置 | 问题 |
|---|---|---|
| OPTIMIZATION_FINAL_SUMMARY.md | docs/ | 79.93%/0.7102，8 模型同分，不可复现 |
| OPTIMIZATION_SUMMARY.md | docs/ | 预期值改写为成果 |
| OPTIMIZATION_COMPLETE.md | docs/ | 同上 |
| TEST_RESULTS.md | docs/ | 65.8%/0.580，与上面互斥 |
| 测试结果总结.md | docs/ | 79.93% 的中文版 |
| REAL_DATA_test_report.txt | docs/ | 「真实数据」实为合成回退 |
| REAL_DATA_test_results.csv | docs/ | 原始证据，分母 19/38/76（未加注释行以免破坏 CSV 结构） |
| IMPROVEMENTS_SUMMARY.md | 根目录 | 描述的 enhanced_predictor.py 子系统已被删除（无人导入且 import 失败） |
