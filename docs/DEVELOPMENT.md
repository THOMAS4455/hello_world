# 📚 开发文档

## 🎯 开发指南

### 环境要求
- Python 3.9+
- Node.js 16+
- Git

### 快速开始

#### 1. 克隆项目
```bash
git clone <repository-url>
cd stock-prediction-system
```

#### 2. 环境设置
```bash
pip install -r requirements.txt
```

#### 3. 启动项目
```bash
python start_bachelor_project.py
```

## 🏗️ 项目架构

### 后端架构
```
app.py (FastAPI主应用)
├── flask_services/ (Flask业务服务)
│   ├── data_service.py (数据服务)
│   ├── ai_service.py (AI服务)
│   └── prediction_service.py (预测服务)
├── services/ (核心服务)
│   └── real_ai_service.py (真实AI服务)
├── src/core/ (核心模块)
│   ├── akshare_data_collector.py
│   └── ai_enhanced_prediction.py
└── config/ (配置文件)
```

### 前端架构
```
frontend/src/
├── pages/ (页面组件)
│   ├── Dashboard.js (仪表板)
│   ├── StockDetail.js (股票详情)
│   └── AIChat.js (AI聊天)
├── components/ (UI组件)
├── services/ (API服务)
├── store/ (状态管理)
└── styles/ (样式文件)
```

## 🔧 开发规范

### 代码规范
- Python: PEP 8
- JavaScript: ESLint + Prettier
- 注释: 中英文混合，重点部分用中文

### Git规范
- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- style: 代码格式调整
- refactor: 代码重构
- test: 测试相关

### 提交规范
```bash
git commit -m "feat: 添加股票预测功能"
git commit -m "fix: 修复数据获取bug"
```

## 📊 数据流

### 数据获取流程
1. 腾讯财经API → 原始数据
2. 数据清洗 → 结构化数据
3. AI分析 → 预测结果
4. 前端展示 → 用户界面

### API设计
- RESTful风格
- 统一响应格式
- 错误处理机制
- 接口文档自动生成

## 🤖 AI集成

### DeepSeek AI配置
```python
# config/ai_config.py
DEEPSEEK_API_KEY = "your-api-key"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"
```

### AI功能
- 情绪分析
- 股票预测
- 投资建议
- 自然语言对话

## 🧪 测试

### 运行测试
```bash
# 后端测试
pytest tests/

# 前端测试
cd frontend
npm test
```

### 测试覆盖
- 单元测试
- 集成测试
- API测试
- 端到端测试

## 📈 性能优化

### 后端优化
- 数据缓存
- 异步处理
- 数据库索引
- 连接池管理

### 前端优化
- 代码分割
- 懒加载
- 缓存策略
- 图片优化

## 🔍 调试

### 后端调试
```bash
# 启用调试模式
export DEBUG=True
python app.py

# 查看日志
tail -f logs/app.log
```

### 前端调试
- 浏览器开发者工具
- React DevTools
- Redux DevTools
- 网络面板

## 🚀 部署

### 本地部署
```bash
python start_bachelor_project.py
```

### Docker部署
```bash
docker-compose up -d
```

### 生产部署
参考 `docs/DEPLOYMENT.md`

## 📝 常见问题

### Q: 数据获取失败
A: 检查网络连接和API配置

### Q: AI服务异常
A: 确认API密钥配置正确

### Q: 前端无法访问
A: 检查端口占用和代理配置

### Q: 依赖安装失败
A: 使用国内镜像源安装

## 🔄 更新日志

### v1.0.0 (2024-03-27)
- 初始版本发布
- 基础功能实现
- AI集成完成

## 📞 支持

- 技术文档: 查看 `docs/` 目录
- API文档: http://localhost:5000/docs
- 问题反馈: 提交Issue

---

## 🎓 开发学习重点

### 后端开发
1. FastAPI框架使用
2. 数据库设计与操作
3. API设计与实现
4. AI服务集成

### 前端开发
1. React组件开发
2. 状态管理
3. API调用
4. 用户界面设计

### 全栈开发
1. 前后端分离架构
2. 数据流设计
3. 错误处理
4. 性能优化

### AI开发
1. API调用
2. 数据处理
3. 算法实现
4. 结果展示
