export const guideContent = {
  'zh-CN': {
    heroTitle: '使用指南与预测原理',
    heroSubtitle: '帮助你在 AlphaScope 里知道「该点哪里、每一步在做什么」',
    heroDesc:
      '本模块面向所有用户（含未登录访客）。建议先读「推荐路径」，再按需查看各功能说明与预测原理。本系统输出的是研究辅助信号，不构成投资建议。',
    tabs: {
      start: '推荐路径',
      features: '功能指南',
      prediction: '预测原理',
      data: '数据与边界',
    },
    start: {
      title: '推荐研究路径',
      steps: [
        {
          title: '1. 看市场与新闻',
          body: '从「情报中心」了解实时财经新闻；进入「市场总览」检索股票、查看涨跌分布与数据源状态。盘外会自动使用当日/上一交易日快照，盘中才会自动刷新行情。',
          path: '/dashboard',
          pathLabel: '进入市场总览',
        },
        {
          title: '2. 选定标的',
          body: '在市场总览或股票详情页确认代码、价格与历史走势。预测与回测都针对单只股票展开，先选好代码再进入下游模块。',
          path: '/dashboard',
          pathLabel: '去选股票',
        },
        {
          title: '3. 生成预测（需登录）',
          body: '在「智能预测」选择股票、预测窗口（horizon）和上涨阈值（up_threshold），点击生成。你会得到方向、置信度、各子模型意见与文字解释。',
          path: '/investment/forecast',
          pathLabel: '打开智能预测',
        },
        {
          title: '4. 回测验证（需登录）',
          body: '在「回测评估」用历史数据检验信号质量，查看准确率、相对基准的提升与 walk-forward 结果。用来判断策略是否稳定，而不是只看一次预测。',
          path: '/investment/backtest',
          pathLabel: '打开回测评估',
        },
        {
          title: '5. AI 研判（需登录）',
          body: '用自然语言追问趋势、风险与策略思路，把结构化信号与自然语言解释结合，再自己做决策。',
          path: '/ai-chat',
          pathLabel: '打开 AI 研判',
        },
      ],
      tips: [
        '首次对某只股票预测可能需要数秒（需训练模型）；相同参数在缓存有效期内再次预测会更快。',
        '登录后可保存预测/回测历史，便于对比不同时间的判断。',
        '任何「上涨/下跌」标签都只是模型对历史规律的统计归纳，不是 guaranteed 结果。',
      ],
    },
    features: {
      title: '各模块做什么',
      items: [
        {
          name: '情报中心',
          path: '/',
          needAuth: false,
          summary: '首页新闻流与模块入口。默认抓取新浪 + 东财等源的当日财经头条，可关键词筛选。',
          how: ['选择新闻来源与数量上限', '点击刷新新闻流', '从卡片跳转至预测、回测等模块'],
        },
        {
          name: '市场总览',
          path: '/dashboard',
          needAuth: false,
          summary: '全市场列表、涨跌筛选、排序与数据源健康面板。',
          how: [
            '交易时段（09:25–15:00）自动约 60 秒刷新；盘外展示快照并提示',
            '手动「刷新数据」可强制拉取实时行情（可能需 1–2 分钟）',
            '点击「详情」进入单股页面',
          ],
        },
        {
          name: '智能预测',
          path: '/investment/forecast',
          needAuth: true,
          summary: '对单只股票给出未来 N 日涨跌方向、置信度与多模型分解结果。',
          how: [
            '选择股票代码',
            '设置 horizon（预测窗口，默认 5 个交易日）',
            '设置 up_threshold（判定「上涨」所需的最小涨幅，默认 2%）',
            '阅读 Decision 卡片、子模型表格与 explanation 文本',
          ],
        },
        {
          name: '回测评估',
          path: '/investment/backtest',
          needAuth: true,
          summary: '在历史区间上模拟信号表现，对比基准准确率。',
          how: [
            '选择与预测相同的 symbol / horizon / threshold',
            '查看 walk-forward、特征重要性与历史 run 记录',
            '关注 improvement 是否为正、样本数是否足够',
          ],
        },
        {
          name: 'AI 研判',
          path: '/ai-chat',
          needAuth: true,
          summary: '对话式解释趋势、风险与策略思路，不替代预测数值本身。',
          how: ['用自然语言提问', '结合你刚看的预测/回测结果追问', '注意 AI 仍可能出错，需人工复核'],
        },
        {
          name: '个人中心 / 设置',
          path: '/profile',
          needAuth: true,
          summary: '资料、偏好与语言；管理员另有「管理台」配置 AI 与数据源。',
          how: ['在设置中切换界面语言', '管理员可查看数据源健康与用户列表'],
        },
      ],
    },
    prediction: {
      title: '预测在算什么',
      intro:
        '系统回答的问题是：「在未来 horizon 个交易日里，收盘价相对当前是否上涨超过 up_threshold？」这是二分类问题（涨/不涨），不是精确价格点位预测。',
      layersTitle: '三层模型结构',
      layers: [
        {
          name: 'Layer 1 · 基线层',
          desc: '随机森林 (RF) 与梯度提升 (GB)，用经典树模型捕捉非线性关系，作为稳健基线。',
        },
        {
          name: 'Layer 2 · 增强层',
          desc: 'Extra Trees、逻辑回归、SVM 等，从不同假设出发补充视角，降低单一模型偏差。',
        },
        {
          name: 'Layer 3 · 状态层',
          desc: '按 bull / bear / range / high_vol 等市场状态路由到不同子模型，适应 regime 切换。',
        },
      ],
      ensemble:
        '最终方向由三层加权集成（约 35% / 40% / 25%），各子模型概率取平均后得到 ensemble 上涨概率，>0.5 判为「上涨类」，否则为「下跌/震荡类」。',
      featuresTitle: '用了哪些特征',
      features: [
        '价格与成交量：均线、动量、波动率、RSI 等技术指标',
        '滞后情绪：前一日新闻情感分数、置信度、正负比例（来自财经头条）',
        '市场广度：全市场上涨/下跌家数比例（滞后注入）',
      ],
      paramsTitle: '关键参数怎么理解',
      params: [
        { key: 'horizon', desc: '向前看几个交易日。越大越偏中期，但可预测性通常下降。' },
        { key: 'up_threshold', desc: '涨幅超过该比例才算「涨」。提高阈值 → 更少但可能更「显著」的上涨样本。' },
        { key: 'confidence', desc: '模型对当前方向的一致性与强度综合评分，不是盈利概率。' },
        { key: 'decision_threshold', desc: '集成上涨概率超过该值才判「涨」。在训练集末尾 15% 验证段上自动搜索（0.35–0.65）。' },
        { key: 'explanation', desc: '基于特征贡献生成的可读摘要，帮助理解「为何偏多/偏空」。' },
      ],
      limitsTitle: '不要过度解读',
      limits: [
        '历史规律不等于未来；黑天鹅、政策与财报会打破统计关系。',
        '置信度高只表示模型内部较一致，不代表一定正确。',
        'A 股 T+1、涨跌停与流动性约束未在模型中完整建模。',
        '本工具用于研究与学习，不构成任何投资建议或承诺收益。',
      ],
    },
    data: {
      title: '数据刷新与系统边界',
      items: [
        {
          q: '行情什么时候会自动更新？',
          a: '交易日 09:25–15:00 约每 60 秒刷新；收盘后、周末与节假日前后使用最近交易日快照，避免无意义的全量拉取。',
        },
        {
          q: '为什么有时加载很慢？',
          a: '全市场实时拉取约 5000+ 只股票，可能需要 1–2 分钟。盘外首次访问会使用已有快照，通常更快。',
        },
        {
          q: '预测为什么第一次慢、第二次快？',
          a: '每只股票首次预测需拉历史 K 线并训练集成模型；相同 symbol + 参数在缓存有效期内会直接复用。',
        },
        {
          q: '回测里的 walk-forward 和线上一致吗？',
          a: '是。滚动验证现在使用与线预测相同的三层集成 + 验证集决策阈值，而不是单独的 LogReg。',
        },
        {
          q: '数据从哪来？',
          a: '行情主要来自东财 push 接口 + 新浪/腾讯直连验证；新闻来自新浪滚动与 AKShare 全球财经；历史 K 线来自 AKShare。',
        },
        {
          q: '情绪/广度历史不足怎么办？',
          a: '管理员可在「管理后台 → 特征历史回填」批量写入：情绪来自近期新闻按日聚合；广度在无法拉全市场历史涨跌家数时，用上证指数日涨跌作有界代理（index_proxy），仅供研究回放。',
        },
      ],
    },
  },
  'en-US': {
    heroTitle: 'User Guide & Prediction Primer',
    heroSubtitle: 'Know where to click and what each step actually does',
    heroDesc:
      'This module is for everyone, including guests. Start with the recommended workflow, then dive into feature guides and how forecasts are built. Outputs are research aids, not investment advice.',
    tabs: {
      start: 'Workflow',
      features: 'Features',
      prediction: 'How Forecasts Work',
      data: 'Data & Limits',
    },
    start: {
      title: 'Recommended workflow',
      steps: [
        {
          title: '1. Scan market & news',
          body: 'Use Intel Hub for headlines and Market Overview for the full watchlist, breadth, and data-health. Live auto-refresh runs during 09:25–15:00; outside sessions you see the latest session snapshot.',
          path: '/dashboard',
          pathLabel: 'Open Market Overview',
        },
        {
          title: '2. Pick a symbol',
          body: 'Confirm code, price, and history on the overview or stock detail page. Forecasts and backtests are single-symbol workflows.',
          path: '/dashboard',
          pathLabel: 'Browse stocks',
        },
        {
          title: '3. Run a forecast (login required)',
          body: 'In Forecasts, choose symbol, horizon, and up_threshold, then generate. You get direction, confidence, per-model votes, and an explanation block.',
          path: '/investment/forecast',
          pathLabel: 'Open Forecasts',
        },
        {
          title: '4. Backtest (login required)',
          body: 'In Backtests, validate signal quality on history: accuracy, lift vs baseline, walk-forward metrics. Use this to judge stability, not a one-off forecast.',
          path: '/investment/backtest',
          pathLabel: 'Open Backtests',
        },
        {
          title: '5. Add AI insights (login required)',
          body: 'AI Chat helps you ask why in plain language, combining structured signals with narrative checks before deciding.',
          path: '/ai-chat',
          pathLabel: 'Open AI Insights',
        },
      ],
      tips: [
        'The first forecast for a symbol may take a few seconds (model training); repeats with the same params are faster while cache is valid.',
        'After login, forecast/backtest runs are stored for comparison over time.',
        'Up/down labels are statistical summaries of history, not guaranteed outcomes.',
      ],
    },
    features: {
      title: 'What each module does',
      items: [
        {
          name: 'Intel Hub',
          path: '/',
          needAuth: false,
          summary: 'Home feed and module shortcuts. Finance headlines from Sina + Eastmoney-style sources with optional keyword filter.',
          how: ['Toggle sources and limit', 'Refresh the feed', 'Jump to forecasts or backtests from cards'],
        },
        {
          name: 'Market Overview',
          path: '/dashboard',
          needAuth: false,
          summary: 'Full watchlist, trend filters, sorting, and data-source health.',
          how: [
            'Auto refresh ~60s during 09:25–15:00; snapshot mode off-hours',
            'Manual refresh forces a live pull (may take 1–2 minutes)',
            'Open stock detail from any row',
          ],
        },
        {
          name: 'Forecasts',
          path: '/investment/forecast',
          needAuth: true,
          summary: 'Direction, confidence, and multi-model breakdown for one symbol.',
          how: [
            'Pick a symbol',
            'Set horizon (default 5 trading days)',
            'Set up_threshold (default 2% move to count as “up”)',
            'Read the decision card, model table, and explanation',
          ],
        },
        {
          name: 'Backtests',
          path: '/investment/backtest',
          needAuth: true,
          summary: 'Historical simulation vs a baseline accuracy.',
          how: [
            'Align symbol / horizon / threshold with your forecast',
            'Inspect walk-forward, feature importance, saved runs',
            'Check whether improvement is positive and samples are sufficient',
          ],
        },
        {
          name: 'AI Insights',
          path: '/ai-chat',
          needAuth: true,
          summary: 'Conversational reasoning about risk and context—not a replacement for numeric forecasts.',
          how: ['Ask in natural language', 'Follow up on a forecast you just ran', 'Treat answers as drafts, not facts'],
        },
        {
          name: 'Profile / Settings',
          path: '/profile',
          needAuth: true,
          summary: 'Account, preferences, language. Admins also get Admin panel for AI and data sources.',
          how: ['Switch UI language in Settings', 'Admins review data health and users'],
        },
      ],
    },
    prediction: {
      title: 'What the forecast means',
      intro:
        'The system asks: “Over the next horizon sessions, will close rise more than up_threshold vs now?” It is binary (up / not-up), not a exact price target.',
      layersTitle: 'Three-layer stack',
      layers: [
        {
          name: 'Layer 1 · Baseline',
          desc: 'Random Forest & Gradient Boosting tree models for a robust nonlinear baseline.',
        },
        {
          name: 'Layer 2 · Enhanced',
          desc: 'Extra Trees, logistic regression, SVM—different inductive biases to reduce single-model risk.',
        },
        {
          name: 'Layer 3 · Regime',
          desc: 'Routes through bull / bear / range / high_vol sub-models when market state shifts.',
        },
      ],
      ensemble:
        'Layers combine with roughly 35% / 40% / 25% weights. Sub-model up-probabilities aggregate to an ensemble score; >0.5 maps to “up class”, else “down/range”.',
      featuresTitle: 'Input features',
      features: [
        'Price & volume: moving averages, momentum, volatility, RSI, etc.',
        'Lagged sentiment: prior-day news scores from finance headlines',
        'Market breadth: rising vs falling stock ratio (lagged)',
      ],
      paramsTitle: 'Key parameters',
      params: [
        { key: 'horizon', desc: 'How many trading days ahead. Longer = more medium-term, often noisier.' },
        { key: 'up_threshold', desc: 'Minimum % gain to label “up”. Higher → fewer but more pronounced up moves.' },
        { key: 'confidence', desc: 'Internal agreement/strength—not P(profit).' },
        { key: 'decision_threshold', desc: 'Ensemble up-probability must exceed this to label “up”. Tuned on the last 15% of the train slice (0.35–0.65).' },
        { key: 'explanation', desc: 'Human-readable summary of feature drivers for the current call.' },
      ],
      limitsTitle: 'Interpret with care',
      limits: [
        'Past patterns ≠ future outcomes; policy shocks and earnings break statistics.',
        'High confidence means model agreement, not certainty.',
        'T+1, limit-up/down, and liquidity rules are not fully modeled.',
        'Research/education only—not investment advice or return promises.',
      ],
    },
    data: {
      title: 'Data refresh & boundaries',
      items: [
        {
          q: 'When does market data auto-refresh?',
          a: 'Weekdays 09:25–15:00 about every 60s. Off-hours and weekends serve the latest session snapshot.',
        },
        {
          q: 'Why is loading sometimes slow?',
          a: 'Full-universe live pulls (~5000+ names) can take 1–2 minutes. Snapshots off-hours are usually faster.',
        },
        {
          q: 'Why is the first forecast slow?',
          a: 'First run per symbol fetches history and trains the ensemble; cached repeats are faster.',
        },
        {
          q: 'What requires login?',
          a: 'Forecasts, backtests, sentiment, AI chat, profile/settings. Home and market overview work for guests.',
        },
        {
          q: 'Where does data come from?',
          a: 'Quotes: Eastmoney push + Sina/Tencent verification. News: Sina roll + AKShare. History: AKShare daily bars.',
        },
        {
          q: 'Sparse sentiment/breadth history?',
          a: 'Admins can run Admin Panel → Feature history backfill: sentiment from recent news by day; breadth uses a bounded Shanghai index daily-return proxy (index_proxy) when full-market advance/decline history is unavailable.',
        },
      ],
    },
  },
};

export const getGuideContent = (language) =>
  guideContent[language === 'en-US' ? 'en-US' : 'zh-CN'] || guideContent['zh-CN'];
