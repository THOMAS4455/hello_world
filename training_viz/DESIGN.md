# 模型训练可视化系统 — 设计文档

## 目录结构

```
training_viz/                    # 独立后端模块
├── DESIGN.md                    # 本设计文档
├── __init__.py
└── reporter.py                  # 训练进度报告器

frontend/src/components/
└── training-viz/                # 独立前端模块
    ├── TrainingVizPanel.js      # 主容器组件
    ├── ModelTrainingCard.js     # 单模型卡片
    ├── LSTMProgressBar.js       # LSTM 状态条
    └── TrainingViz.css          # 样式
```

## 数据流

```
ImprovePredictor.train()
    │  进度回调 (per-model CV scores)
    ▼
TrainingProgressReporter
    │  update_training() → task_manager
    ▼
GET /api/tasks/status?task_id=xxx  (已有轮询 1.2s)
    │  { training_details: { models: {...}, current_model: ..., ... } }
    ▼
PredictionTasksContext (PROGRESS reducer + trainingDetails)
    │
    ▼
TrainingVizPanel  →  ModelTrainingCard × N  →  LSTMProgressBar
```

## 每个模型训练时的 UI 卡片状态

| 状态 | 左边框颜色 | 图标 | 显示内容 |
|------|-----------|------|---------|
| pending | 灰色 | ○ | 模型名 |
| training | 蓝色 + 脉冲动画 | ◌ | 模型名 |
| done | 绿色 | ✓ | 模型名 + CV均值 ± 标准差 |
| error | 红色 | ✗ | 模型名 + 错误信息 |

## 需要修改的现有文件（共5个）

1. `flask_services/task_manager.py` — 加 3 行 `update_training()`
2. `src/core/improved_predictor.py` — train() 加 progress_callback 参数 + 10个回调点
3. `flask_services/prediction_service.py` — 有 task_id 时创建 Reporter，传给 train()
4. `frontend/contexts/PredictionTasksContext.js` — reducer 加 trainingDetails 字段
5. `frontend/pages/investment/ForecastPage.js` + `BacktestPage.js` — 嵌入 TrainingVizPanel

## 实现步骤（6个阶段）

Phase 1: 后端基础 — 创建 training_viz/reporter.py + 修改 3 个后端文件
Phase 2: 后端验证 — 手动测试 training_details 字段出现在 poll 响应中
Phase 3: 前端 Context — 扩展 reducer 捕获 trainingDetails
Phase 4: 前端组件 — 创建 3 个新组件 + 1 个 CSS
Phase 5: 前端集成 — ForecastPage/BacktestPage 嵌入 TrainingVizPanel
Phase 6: 端到端测试 — 完整流程 + 边界情况
