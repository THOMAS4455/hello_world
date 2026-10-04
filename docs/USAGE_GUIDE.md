# 优化后的股票预测系统 - 使用指南

## 📋 系统概述

本系统已完成核心优化，具备以下能力：
- ✅ **90个预测特征**（增长260%）
- ✅ **8个机器学习模型**（增长60%）
- ✅ **智能数据预处理**
- ✅ **制度检测和路由**

---

## 🚀 快速开始

### 1. 环境准备

确保已安装所有依赖：

```bash
cd d:\IdeaProject\untitled\stock-prediction-system\stock-prediction-system
py -m pip install -r requirements.txt
```

关键依赖：
- `lightgbm>=4.0.0`
- `xgboost>=2.0.0`
- `catboost>=1.2.0`
- `scikit-learn>=1.3.0`
- `pandas>=2.2.3`
- `numpy>=1.26.4`

### 2. 验证安装

运行验证脚本：

```bash
# 验证模型集成
py scripts\verify_models.py

# 验证特征工程
py scripts\verify_features.py
```

预期输出：
```
✓ LightGBM integrated in baseline layer
✓ XGBoost integrated in enhanced layer
✓ CatBoost integrated in enhanced layer
✓ Total models: 8
✓ Feature count: 90
```

### 3. 性能测试

运行性能测试：

```bash
# 简单性能测试（使用合成数据）
py simple_performance_test.py

# 或使用批处理文件
run_test.bat
```

---

## 💻 代码使用示例

### 基础使用

```python
from src.core.improved_predictor import ImprovedPredictor
import pandas as pd

# 1. 准备数据（需要OHLCV列）
df = pd.DataFrame({
    'date': [...],
    'close_price': [...],
    'high_price': [...],
    'low_price': [...],
    'open_price': [...],
    'volume': [...]
})

# 2. 初始化预测器（自动加载8个模型）
predictor = ImprovedPredictor()

# 3. 特征工程（自动生成90个特征）
features = predictor.prepare_features(df)
print(f"生成了 {len(predictor.feature_columns)} 个特征")

# 4. 准备标签
labels = predictor.prepare_labels(df, horizon=5, up_threshold=0.02)

# 5. 对齐特征和标签
from src.core.improved_predictor import align_features_and_labels
X, y = align_features_and_labels(features, labels)

print(f"有效样本数: {len(X)}")
print(f"上涨样本比例: {y.mean()*100:.1f}%")
```

### 训练模型

```python
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score

# 1. 划分训练集和测试集
train_size = int(len(X) * 0.7)
X_train = X.iloc[:train_size]
y_train = y.iloc[:train_size]
X_test = X.iloc[train_size:]
y_test = y.iloc[train_size:]

# 2. 标准化特征
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train[predictor.feature_columns])
X_test_scaled = scaler.transform(X_test[predictor.feature_columns])

# 3. 训练单个模型（例如LightGBM）
lgb_model = predictor.layer_models['baseline']['lgb']
lgb_model.fit(X_train_scaled, y_train)

# 4. 预测和评估
test_pred = lgb_model.predict(X_test_scaled)
test_acc = accuracy_score(y_test, test_pred)
test_f1 = f1_score(y_test, test_pred, average='weighted')

print(f"测试准确率: {test_acc*100:.2f}%")
print(f"F1分数: {test_f1:.4f}")
```

### 训练所有模型并比较

```python
results = {}

for layer_name in ['baseline', 'enhanced']:
    for model_name, model in predictor.layer_models[layer_name].items():
        # 训练
        model.fit(X_train_scaled, y_train)
        
        # 预测
        train_pred = model.predict(X_train_scaled)
        test_pred = model.predict(X_test_scaled)
        
        # 评估
        train_acc = accuracy_score(y_train, train_pred)
        test_acc = accuracy_score(y_test, test_pred)
        test_f1 = f1_score(y_test, test_pred, average='weighted')
        
        results[f"{layer_name}:{model_name}"] = {
            'train_acc': train_acc,
            'test_acc': test_acc,
            'f1': test_f1,
            'gap': train_acc - test_acc
        }
        
        print(f"{layer_name}:{model_name}")
        print(f"  训练准确率: {train_acc*100:.2f}%")
        print(f"  测试准确率: {test_acc*100:.2f}%")
        print(f"  F1分数: {test_f1:.4f}")
        print(f"  过拟合程度: {(train_acc - test_acc)*100:.2f}%")
        print()

# 找出最佳模型
best_model = max(results.items(), key=lambda x: x[1]['test_acc'])
print(f"最佳模型: {best_model[0]}")
print(f"测试准确率: {best_model[1]['test_acc']*100:.2f}%")
```

### 使用制度检测

```python
# 获取市场制度
regime_labels = predictor._derive_regime_labels(features)

print("市场制度分布:")
print(regime_labels.value_counts())

# 按制度分组训练
for regime in ['bull', 'bear', 'range', 'high_vol']:
    regime_mask = regime_labels == regime
    if regime_mask.sum() > 50:  # 确保有足够样本
        X_regime = X[regime_mask]
        y_regime = y[regime_mask]
        print(f"\n{regime}市场: {len(X_regime)} 样本")
```

---

## 📊 特征说明

### 特征类别

系统自动生成90个特征，分为5大类：

#### 1. 基础技术指标（17个）
- 移动平均: ma5, ma10, ma20, ma60
- 价格变化: price_change, price_change_2d, price_change_5d
- 波动率: volatility, volatility_30
- 成交量: volume_ratio
- RSI, MACD, Bollinger Bands
- 趋势强度: trend_strength, ma60_gap

#### 2. 情感特征（8个）
- sentiment_score_lag1
- sentiment_confidence_lag1
- positive_ratio_lag1
- negative_ratio_lag1
- market_breadth_lag1
- target_match_count_lag1
- sentiment_decay_lag1
- sentiment_available

#### 3. 时间序列特征（20个）
- **滞后特征**: price_change_lag[1,2,3,5,10], volume_lag[1,2,3]
- **滚动统计**: rolling_mean[5,10,20], rolling_std[5,10,20], rolling_skew_20
- **指数移动平均**: ema[5,10,20,50]
- **自相关**: price_autocorr_1

#### 4. 交叉特征（30个）
- **技术×情感**: rsi_x_sentiment, macd_x_sentiment_conf等
- **技术×成交量**: price_change_x_volume_ratio, volatility_x_volume等
- **技术×市场广度**: trend_strength_x_market_breadth等
- **多维交互**: rsi_x_sentiment_div_volatility等
- **复合指标**: sentiment_momentum, composite_signal等

#### 5. 微观结构特征（15个）
- **价差**: high_low_spread, open_close_spread, intraday_range
- **价格影响**: volume_price_impact, large_trade_indicator
- **订单流**: buy_sell_imbalance_proxy, tick_direction
- **流动性**: amihud_illiquidity, turnover_rate, bid_ask_spread_proxy
- **波动率**: realized_volatility, garman_klass_volatility, parkinson_volatility等

---

## 🤖 模型说明

### Baseline层（3个模型）

1. **RandomForestClassifier**
   - n_estimators=160
   - 集成学习，抗过拟合
   - 适合非线性关系

2. **GradientBoostingClassifier**
   - n_estimators=160
   - 顺序提升，高精度
   - 适合复杂模式

3. **LightGBMClassifier** ⭐ 新增
   - n_estimators=200, learning_rate=0.05
   - 快速训练，高效内存使用
   - 适合大规模数据

### Enhanced层（5个模型）

1. **ExtraTreesClassifier**
   - n_estimators=220
   - 极端随机树，降低方差

2. **LogisticRegression**
   - max_iter=2000
   - 线性模型，可解释性强

3. **SVC**
   - kernel='rbf', probability=True
   - 支持向量机，适合高维数据

4. **XGBClassifier** ⭐ 新增
   - n_estimators=200, learning_rate=0.05
   - 优化的梯度提升，高性能
   - 内置正则化

5. **CatBoostClassifier** ⭐ 新增
   - iterations=200, learning_rate=0.05
   - 处理类别特征优秀
   - 抗过拟合能力强

### 集成策略

- **三层加权**: baseline(35%) + enhanced(40%) + regime(25%)
- **制度路由**: 根据市场状态自动选择最佳模型
- **4种制度**: bull, bear, range, high_vol

---

## ⚙️ 配置参数

### 特征工程参数

```python
# 在prepare_features()中
# NaN填充限制
fillna_limit = 5  # 前向填充最多5期

# 在prepare_labels()中
horizon = 5  # 预测未来5天
up_threshold = 0.02  # 上涨阈值2%
```

### 模型参数

所有模型参数在`ImprovedPredictor.__init__()`中定义，可以根据需要调整：

```python
predictor = ImprovedPredictor()

# 修改LightGBM参数
predictor.layer_models['baseline']['lgb'].set_params(
    n_estimators=300,
    learning_rate=0.03,
    max_depth=8
)

# 修改集成权重
predictor.layer_weights = {
    'baseline': 0.4,
    'enhanced': 0.4,
    'regime': 0.2
}
```

---

## 📈 性能优化建议

### 1. 数据质量
- 确保至少500行历史数据
- 检查OHLCV数据完整性
- 处理异常值和缺失值

### 2. 特征选择
如果计算资源有限，可以选择性使用特征：

```python
# 只使用重要特征
important_features = [
    'ma5', 'ma10', 'ma20', 'rsi', 'macd',
    'price_change_lag1', 'volume_ratio',
    'rsi_x_sentiment', 'composite_signal'
]

X_train_selected = X_train[important_features]
```

### 3. 模型选择
根据场景选择模型：

- **速度优先**: LightGBM, RandomForest
- **准确率优先**: XGBoost, CatBoost
- **可解释性**: LogisticRegression
- **稳定性**: 集成所有模型

### 4. 超参数优化（可选）

```python
from optuna import create_study

def objective(trial):
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 100, 300),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1),
        'max_depth': trial.suggest_int('max_depth', 5, 10)
    }
    
    model = lgb.LGBMClassifier(**params, random_state=42)
    model.fit(X_train_scaled, y_train)
    pred = model.predict(X_test_scaled)
    return f1_score(y_test, pred, average='weighted')

study = create_study(direction='maximize')
study.optimize(objective, n_trials=50)
print(f"最佳参数: {study.best_params}")
```

---

## 🐛 常见问题

### Q1: 特征生成后行数为0
**原因**: 数据量不足，滚动窗口特征需要历史数据  
**解决**: 确保至少100行输入数据

### Q2: 模型训练很慢
**原因**: 8个模型同时训练，计算量大  
**解决**: 
- 只训练需要的模型
- 减少n_estimators
- 使用更少的特征

### Q3: 准确率不理想
**原因**: 数据质量、参数设置、样本不平衡  
**解决**:
- 检查数据质量
- 调整up_threshold
- 使用样本平衡技术（SMOTE）
- 超参数优化

### Q4: 内存不足
**原因**: 90个特征 × 大量样本  
**解决**:
- 减少特征数量
- 分批处理数据
- 使用特征选择

---

## 📝 最佳实践

### 1. 数据准备
```python
# 确保数据格式正确
assert 'close_price' in df.columns
assert 'high_price' in df.columns
assert 'low_price' in df.columns
assert 'open_price' in df.columns
assert 'volume' in df.columns

# 检查数据量
assert len(df) >= 100, "需要至少100行数据"

# 检查数据类型
df['close_price'] = df['close_price'].astype(float)
df['volume'] = df['volume'].astype(float)
```

### 2. 训练流程
```python
# 1. 时间序列分割（不要随机分割）
train_size = int(len(X) * 0.7)
X_train = X.iloc[:train_size]
X_test = X.iloc[train_size:]

# 2. 标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train[predictor.feature_columns])
X_test_scaled = scaler.transform(X_test[predictor.feature_columns])

# 3. 训练
model.fit(X_train_scaled, y_train)

# 4. 评估
test_pred = model.predict(X_test_scaled)
print(f"准确率: {accuracy_score(y_test, test_pred)*100:.2f}%")
```

### 3. 模型保存
```python
import joblib

# 保存模型和scaler
joblib.dump(model, 'model.pkl')
joblib.dump(scaler, 'scaler.pkl')
joblib.dump(predictor.feature_columns, 'features.pkl')

# 加载
model = joblib.load('model.pkl')
scaler = joblib.load('scaler.pkl')
feature_columns = joblib.load('features.pkl')
```

---

## 📞 技术支持

### 文档
- `PROGRESS_REPORT.md` - 完整进度报告
- `OPTIMIZATION_STATUS.md` - 详细状态跟踪
- `README.md` - 项目说明

### 脚本
- `scripts/verify_models.py` - 模型验证
- `scripts/verify_features.py` - 特征验证
- `simple_performance_test.py` - 性能测试

### 关键文件
- `src/core/improved_predictor.py` - 主预测器类
- `requirements.txt` - 依赖列表

---

## 🎯 性能目标

| 指标 | 目标 | 说明 |
|------|------|------|
| 测试准确率 | ≥65% | 在测试集上的分类准确率 |
| F1分数 | ≥0.60 | 综合考虑精确率和召回率 |
| 训练-测试差距 | <5% | 过拟合程度指标 |
| 夏普比率 | >1.0 | 回测交易策略的风险调整收益 |

---

**版本**: v2.0-optimized  
**更新日期**: 2025-01-28  
**作者**: Kiro AI Assistant
