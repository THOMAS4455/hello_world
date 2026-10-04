import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Badge, Button, Card, ProgressBar, Spinner } from 'react-bootstrap';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { usePredictionTasks } from '../contexts/PredictionTasksContext';
import { useAppI18n } from '../i18n';
import '../styles/TrainingMonitor.css';

const DISPLAY_NAMES = {
  'baseline:rf': 'Random Forest', 'baseline:gb': 'Gradient Boost', 'baseline:lgb': 'LightGBM',
  'enhanced:extra_trees': 'Extra Trees', 'enhanced:log_reg': 'Logistic Reg.', 'enhanced:svm': 'SVM (RBF)',
  'enhanced:xgb': 'XGBoost', 'enhanced:catboost': 'CatBoost',
};

const LAYER_ORDER = ['baseline', 'enhanced'];
const LAYER_LABELS = { baseline: 'Layer 1 · Baseline', enhanced: 'Layer 2 · Enhanced' };
const REGIME_NAMES = { bull: '牛市', bear: '熊市', range: '震荡', high_vol: '高波动' };
const REGIME_ICONS = { bull: '🐂', bear: '🐻', range: '📊', high_vol: '⚡' };

const TrainingMonitor = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const navigate = useNavigate();
  const { taskList, dismissTask, cancelTask, markSeen } = usePredictionTasks();
  const roles = useSelector((s) => s?.auth?.roles || []);
  const isAdmin = Array.isArray(roles) && roles.some((r) => String(r).toLowerCase() === 'admin');

  const [selectedId, setSelectedId] = useState(null);

  const visibleTasks = useMemo(() => taskList.slice(0, 20), [taskList]);

  useEffect(() => {
    if (visibleTasks.length > 0 && !selectedId) {
      setSelectedId(visibleTasks[0].id);
    }
  }, [visibleTasks, selectedId]);

  const activeTask = useMemo(
    () => visibleTasks.find((t) => t.id === selectedId) || null,
    [visibleTasks, selectedId],
  );

  const td = activeTask?.trainingDetails;

  const groupedModels = useMemo(() => {
    if (!td?.models) return {};
    const layers = {};
    Object.entries(td.models).forEach(([mid, info]) => {
      const layer = info?.layer || mid.split(':')[0] || 'other';
      if (!layers[layer]) layers[layer] = [];
      layers[layer].push({ id: mid, ...info });
    });
    return layers;
  }, [td]);

  const handleCancel = useCallback(
    (e, tid) => { e.stopPropagation(); cancelTask(tid); },
    [cancelTask],
  );

  const handleDismiss = useCallback(
    (e, tid) => { e.stopPropagation(); dismissTask(tid); if (selectedId === tid) setSelectedId(null); },
    [dismissTask, selectedId],
  );

  if (!isAdmin) {
    return (
      <div className="analysis-page tm-page text-center mt-5">
        <h2>{isEnglish ? 'Admin Access Required' : '需要管理员权限'}</h2>
        <p className="text-muted">{isEnglish ? 'The training monitor is only available to administrators.' : '训练监控台仅限管理员访问。'}</p>
      </div>
    );
  }

  const fmtPct = (v) => (typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : '-');
  const statusTag = (s) => {
    if (s === 'running') return <Badge bg="primary" className="ms-1">运行中</Badge>;
    if (s === 'done') return <Badge bg="success" className="ms-1">完成</Badge>;
    if (s === 'error') return <Badge bg="danger" className="ms-1">失败</Badge>;
    if (s === 'cancelled') return <Badge bg="secondary" className="ms-1">已取消</Badge>;
    return null;
  };

  return (
    <div className="analysis-page tm-page">
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 650, letterSpacing: '-.02em' }}>
          {isEnglish ? 'Model Training Monitor' : '模型训练监控台'}
        </h1>
        <p className="text-muted" style={{ margin: 0 }}>
          {isEnglish ? 'Real-time visibility into ML model training across all prediction tasks.' : '实时查看所有预测任务的模型训练过程。'}
        </p>
      </div>

      <div className="tm-layout">
        {/* ── Left: Task list ── */}
        <div className="tm-sidebar">
          <Card className="tm-sidebar-card">
            <Card.Header style={{ fontSize: '.78rem', fontWeight: 650 }}>
              {isEnglish ? 'Tasks' : '任务列表'} ({visibleTasks.length})
            </Card.Header>
            <Card.Body style={{ padding: 0 }}>
              {visibleTasks.length === 0 ? (
                <div className="text-muted text-center py-4" style={{ fontSize: '.82rem' }}>
                  {isEnglish ? 'No training tasks yet. Run a forecast or backtest.' : '暂无训练任务。运行预测或回测后出现。'}
                </div>
              ) : (
                visibleTasks.map((t) => (
                  <div
                    key={t.id}
                    className={`tm-task-item ${selectedId === t.id ? 'active' : ''}`}
                    onClick={() => { setSelectedId(t.id); if (t.status !== 'running') markSeen(t.id); }}
                    role="button"
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span className={`tm-status-dot ${t.status}`} />
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '.78rem' }}>
                          {t.type === 'forecast' ? '预测' : t.type === 'backtest' ? '回测' : t.type}
                          <span className="text-muted ms-1" style={{ fontSize: '.7rem' }}>{t.symbol}</span>
                        </div>
                        <div style={{ fontSize: '.68rem', color: 'var(--ds-text-tertiary)' }}>
                          {new Date(t.startedAt).toLocaleTimeString()}
                          {statusTag(t.status)}
                        </div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {t.status === 'done' && t.route && (
                        <Button size="sm" variant="link" className="p-0" style={{ fontSize: '.68rem' }}
                          onClick={(e) => { e.stopPropagation(); navigate(t.route); }}>
                          {isEnglish ? 'View' : '查看'}
                        </Button>
                      )}
                      <button className="tm-close-btn" onClick={(e) => handleDismiss(e, t.id)}>×</button>
                    </div>
                  </div>
                ))
              )}
            </Card.Body>
          </Card>
        </div>

        {/* ── Right: Detail ── */}
        <div className="tm-content">
          {!activeTask ? (
            <Card><Card.Body className="text-center text-muted py-5">{isEnglish ? 'Select a task to view details.' : '选择一个任务查看详情。'}</Card.Body></Card>
          ) : activeTask.status === 'running' && td ? (
            <>
              {/* Progress header */}
              <Card className="mb-2">
                <Card.Body style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Spinner size="sm" style={{ color: 'var(--ds-accent)' }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '.82rem', fontWeight: 650 }}>
                      {activeTask.type === 'forecast' ? '预测' : '回测'}
                      {activeTask.symbol ? ` · ${activeTask.symbol}` : ''}
                    </div>
                    <div style={{ fontSize: '.72rem', color: 'var(--ds-text-tertiary)' }}>
                      {td.current_model || '准备中'} · {td.models_trained || 0}/{td.total_models || 0} 模型完成
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <ProgressBar now={activeTask.progress || 0} style={{ width: 120, height: 6 }} animated />
                    <span style={{ fontSize: '.78rem', fontWeight: 650, color: 'var(--ds-accent)' }}>{activeTask.progress || 0}%</span>
                  </div>
                  <Button size="sm" variant="outline-danger" style={{ fontSize: '.68rem' }} onClick={(e) => handleCancel(e, activeTask.id)}>
                    {isEnglish ? 'Cancel' : '取消'}
                  </Button>
                </Card.Body>
              </Card>

              {/* Main model layers */}
              {LAYER_ORDER.map((ln) => {
                const items = groupedModels[ln];
                if (!items || items.length === 0) return null;
                const layerDone = items.filter((m) => m.status === 'done').length;
                const isActive = td.current_layer === ln;
                return (
                  <Card key={ln} className="mb-2">
                    <Card.Header style={{ fontSize: '.76rem', fontWeight: 650, display: 'flex', justifyContent: 'space-between' }}>
                      <span>{LAYER_LABELS[ln] || ln}</span>
                      <span><span className={`tm-tag ${isActive ? 'active' : layerDone === items.length ? 'done' : ''}`}>{layerDone}/{items.length}</span></span>
                    </Card.Header>
                    <Card.Body style={{ padding: '10px 14px' }}>
                      <div className="tm-mgrid">
                        {items.map((m) => (
                          <div key={m.id} className={`tm-mc ${m.status}`}>
                            <div className="tm-mc-name">{DISPLAY_NAMES[m.id] || m.id}</div>
                            {m.status === 'done' && m.cv_mean != null ? (
                              <div className="tm-mc-score">{(m.cv_mean * 100).toFixed(1)}%</div>
                            ) : m.status === 'training' ? (
                              <div className="tm-mc-meta" style={{ color: 'var(--ds-accent)' }}>训练中…</div>
                            ) : (
                              <div className="tm-mc-meta">等待中</div>
                            )}
                            {m.status === 'done' && m.cv_std != null && (
                              <div className="tm-mc-meta">±{(m.cv_std * 100).toFixed(1)}%</div>
                            )}
                          </div>
                        ))}
                      </div>
                    </Card.Body>
                  </Card>
                );
              })}

              {/* Regime */}
              {td.regime && (
                <Card className="mb-2">
                  <Card.Header style={{ fontSize: '.76rem', fontWeight: 650 }}>
                    Layer 3 · Regime
                    <span className={`tm-tag ms-2 ${td.regime.status}`}>{td.regime.regimes_trained?.length || 0}/4</span>
                  </Card.Header>
                  <Card.Body style={{ padding: '10px 14px' }}>
                    <div className="tm-mgrid">
                      {['bull', 'bear', 'range', 'high_vol'].map((r) => {
                        const done = td.regime.regimes_trained?.includes(r);
                        return (
                          <div key={r} className={`tm-mc ${done ? 'done' : td.regime.status === 'training' ? 'running' : 'pending'}`}>
                            <div className="tm-mc-name">{REGIME_ICONS[r]} {REGIME_NAMES[r] || r}</div>
                            <div className="tm-mc-meta">{done ? '完成' : '等待中'}</div>
                          </div>
                        );
                      })}
                    </div>
                  </Card.Body>
                </Card>
              )}

              {/* LSTM */}
              {td.lstm && (
                <Card className="mb-2">
                  <Card.Body style={{ padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: '.76rem', fontWeight: 650 }}>🧠 LSTM</span>
                    <span className={`tm-tag ${td.lstm.status}`}>
                      {td.lstm.status === 'done' ? '完成' : td.lstm.status === 'training' ? '训练中' : td.lstm.status === 'skipped' ? '已跳过' : '等待'}
                    </span>
                    {td.lstm.message && <span style={{ fontSize: '.7rem', color: 'var(--ds-text-tertiary)' }}>{td.lstm.message}</span>}
                  </Card.Body>
                </Card>
              )}

              {/* Weight optimization */}
              {td.weight_optimization && (
                <Card>
                  <Card.Body style={{ padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: '.76rem', fontWeight: 650 }}>⚖️ Weight Optimization</span>
                    <span className={`tm-tag ${td.weight_optimization.status}`}>
                      {td.weight_optimization.status === 'done' ? '完成' : td.weight_optimization.status === 'training' ? '学习中' : '等待'}
                    </span>
                  </Card.Body>
                </Card>
              )}
            </>
          ) : activeTask.status === 'done' ? (
            <Card>
              <Card.Header style={{ fontSize: '.82rem', fontWeight: 650, display: 'flex', justifyContent: 'space-between' }}>
                <span>✅ {activeTask.type === 'forecast' ? '预测' : '回测'} 完成 · {activeTask.symbol}</span>
                <span style={{ fontSize: '.7rem', color: 'var(--ds-text-tertiary)' }}>
                  {new Date(activeTask.completedAt).toLocaleTimeString()}
                </span>
              </Card.Header>
              <Card.Body className="text-center py-4">
                <p className="text-muted">{isEnglish ? 'Training completed successfully.' : '训练已完成。'}</p>
                {activeTask.route && (
                  <Button variant="primary" onClick={() => navigate(activeTask.route)}>
                    {isEnglish ? 'View Result' : '查看结果'}
                  </Button>
                )}
              </Card.Body>
            </Card>
          ) : activeTask.status === 'error' ? (
            <Card><Card.Body className="text-center text-danger py-4">{activeTask.error || (isEnglish ? 'Task failed.' : '任务失败。')}</Card.Body></Card>
          ) : (
            <Card><Card.Body className="text-center text-muted py-5">{isEnglish ? 'No training details available.' : '暂无训练详情。'}</Card.Body></Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default TrainingMonitor;
