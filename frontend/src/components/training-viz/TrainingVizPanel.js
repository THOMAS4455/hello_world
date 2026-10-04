import React, { useMemo } from 'react';
import { useSelector } from 'react-redux';
import { ProgressBar, Spinner } from 'react-bootstrap';
import { usePredictionTasks } from '../../contexts/PredictionTasksContext';
import { useAppI18n } from '../../i18n';
import './TrainingViz.css';

const LAYER_ORDER = ['baseline', 'enhanced', 'regime'];

const DISPLAY_NAMES = {
  'baseline:rf': 'Random Forest',
  'baseline:gb': 'Gradient Boost',
  'baseline:lgb': 'LightGBM',
  'enhanced:extra_trees': 'Extra Trees',
  'enhanced:log_reg': 'Logistic Reg.',
  'enhanced:svm': 'SVM (RBF)',
  'enhanced:xgb': 'XGBoost',
  'enhanced:catboost': 'CatBoost',
};

const ModelCard = ({ modelId, info }) => {
  const status = info?.status || 'pending';
  const name = DISPLAY_NAMES[modelId] || modelId;
  const cls = status === 'done' ? 'done' : status === 'training' ? 'running' : 'pending';

  return (
    <div className={`tr-mc ${cls}`}>
      <div className="mc-name">
        <span>{name}</span>
        {status === 'done' && info?.cv_mean != null && (
          <span style={{ fontFamily: 'monospace', fontSize: '.78rem', color: '#30a46c' }}>
            {(info.cv_mean * 100).toFixed(1)}%
          </span>
        )}
      </div>
      {status === 'done' && info?.cv_mean != null ? (
        <div className="mc-score">CV {(info.cv_mean * 100).toFixed(1)}%</div>
      ) : status === 'training' ? (
        <div className="mc-meta" style={{ color: 'var(--ds-accent)' }}>
          <Spinner size="sm" className="me-1" style={{ width: 10, height: 10 }} />
          训练中…
        </div>
      ) : (
        <div className="mc-meta">等待中</div>
      )}
      {status === 'done' && info?.cv_std != null && (
        <div className="mc-meta">±{(info.cv_std * 100).toFixed(1)}%</div>
      )}
    </div>
  );
};

const TrainingVizPanel = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const { taskList } = usePredictionTasks();
  const roles = useSelector((state) => state?.auth?.roles || []);
  const isAdmin = Array.isArray(roles) && roles.some((r) => String(r).toLowerCase() === 'admin');

  const activeTask = useMemo(() => {
    return taskList.find((t) => t.status === 'running' && t.trainingDetails) || null;
  }, [taskList]);

  const td = activeTask?.trainingDetails;
  if (!isAdmin || !td) return null;

  const models = td.models || {};
  const layers = {};
  Object.entries(models).forEach(([mid, info]) => {
    const layer = info?.layer || mid.split(':')[0] || 'other';
    if (!layers[layer]) layers[layer] = [];
    layers[layer].push({ id: mid, ...info });
  });

  const doneCount = Object.values(models).filter((m) => m?.status === 'done').length;
  const totalCount = td.total_models || Object.keys(models).length || 0;

  return (
    <div className="training-panel">
      <div className="training-panel-header">
        <span style={{ color: 'var(--ds-accent)' }}>
          <Spinner size="sm" style={{ width: 14, height: 14 }} className="me-2" />
        </span>
        <span>模型训练中</span>
        <span style={{ fontSize: '.7rem', color: 'var(--ds-text-tertiary)', marginLeft: 'auto' }}>
          {td.current_model || '...'} ({doneCount}/{totalCount})
        </span>
        <ProgressBar
          now={activeTask.progress || 0}
          style={{ width: 120, height: 4 }}
          className="ms-2"
        />
      </div>
      <div className="training-panel-body">
        {LAYER_ORDER.map((layerName) => {
          const items = layers[layerName];
          if (!items || items.length === 0) return null;
          const layerDone = items.filter((m) => m.status === 'done').length;
          const isActive = td.current_layer === layerName;
          return (
            <div key={layerName}>
              <div className="tr-section-label">
                {layerName === 'baseline' ? 'Layer 1 · Baseline' : layerName === 'enhanced' ? 'Layer 2 · Enhanced' : 'Layer 3 · Regime'}
                <span className={`tr-tag ${isActive ? 'active' : layerDone === items.length ? 'done' : ''}`}>
                  {layerDone}/{items.length}
                </span>
              </div>
              <div className="tr-mgrid">
                {items.map((m) => (
                  <ModelCard key={m.id} modelId={m.id} info={m} />
                ))}
              </div>
            </div>
          );
        })}

        {td.lstm && (
          <div className="tr-section-label" style={{ marginTop: 10 }}>
            LSTM · {td.lstm.status === 'done' ? '完成' : td.lstm.status === 'training' ? '训练中' : '等待'}
          </div>
        )}
        {td.weight_optimization && (
          <div className="tr-section-label">
            Weight Optimization · {td.weight_optimization.status === 'done' ? '完成' : '等待'}
          </div>
        )}
      </div>
    </div>
  );
};

export default TrainingVizPanel;
