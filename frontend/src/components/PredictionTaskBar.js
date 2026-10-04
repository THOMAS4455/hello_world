import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Badge, ProgressBar, Spinner } from 'react-bootstrap';
import { useLocation, useNavigate } from 'react-router-dom';
import { usePredictionTasks } from '../contexts/PredictionTasksContext';
import { useAppI18n } from '../i18n';
import '../styles/PredictionTaskBar.css';

const TYPE_LABELS = {
  forecast: { en: 'Forecast', zh: '预测' },
  backtest: { en: 'Backtest', zh: '回测' },
  portfolio: { en: 'Portfolio', zh: '组合' },
  paper: { en: 'Paper', zh: '模拟盘' },
};

const STAGE_LABELS = {
  loading_data: { en: 'Fetching data', zh: '获取数据' },
  training_models: { en: 'Training models', zh: '训练模型' },
  running_backtest: { en: 'Running backtest', zh: '运行回测' },
  generating_prediction: { en: 'Generating prediction', zh: '生成预测' },
  building_result: { en: 'Building report', zh: '构建报告' },
};

const PredictionTaskBar = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const navigate = useNavigate();
  const location = useLocation();
  const { taskList, markSeen, dismissTask, cancelTask, cleanup } = usePredictionTasks();
  const [expanded, setExpanded] = useState(false);
  const prevCountRef = useRef(0);

  const typeLabel = useCallback(
    (type) => {
      const labels = TYPE_LABELS[type] || {};
      return isEnglish ? (labels.en || type) : (labels.zh || type);
    },
    [isEnglish],
  );

  const stageLabel = useCallback(
    (stage) => {
      const labels = STAGE_LABELS[stage];
      if (!labels) return stage || '';
      return isEnglish ? labels.en : labels.zh;
    },
    [isEnglish],
  );

  const visibleTasks = useMemo(() => {
    return taskList.slice(0, 8).filter((t) => {
      if (t.status === 'running') return true;
      const age = Date.now() - t.completedAt;
      return age < 10 * 60 * 1000;
    });
  }, [taskList]);

  const runningTasks = useMemo(() => visibleTasks.filter((t) => t.status === 'running'), [visibleTasks]);
  const doneTasks = useMemo(() => visibleTasks.filter((t) => t.status !== 'running'), [visibleTasks]);

  useEffect(() => {
    const timer = setInterval(cleanup, 30000);
    return () => clearInterval(timer);
  }, [cleanup]);

  // Auto-expand when a new task appears, then auto-collapse after 8 seconds
  useEffect(() => {
    if (visibleTasks.length > 0 && visibleTasks.length > prevCountRef.current) {
      setExpanded(true);
      const timer = setTimeout(() => setExpanded(false), 8000);
      prevCountRef.current = visibleTasks.length;
      return () => clearTimeout(timer);
    }
    prevCountRef.current = visibleTasks.length;
  }, [visibleTasks.length]);

  const handleTaskClick = useCallback(
    (task) => {
      if (task.status !== 'running') markSeen(task.id);
      if (task.route && location.pathname !== task.route) navigate(task.route);
    },
    [markSeen, navigate, location.pathname],
  );

  const handleCancel = useCallback(
    (e, task) => {
      e.stopPropagation();
      cancelTask(task.id);
    },
    [cancelTask],
  );

  const handleDismiss = useCallback(
    (e, task) => {
      e.stopPropagation();
      dismissTask(task.id);
    },
    [dismissTask],
  );

  if (visibleTasks.length === 0) return null;

  return (
    <div
      className={`task-bar task-bar--visible${expanded ? ' task-bar--expanded' : ''}`}
      onMouseEnter={() => setExpanded(true)}
      onMouseLeave={() => {
        if (runningTasks.length === 0) setExpanded(false);
      }}
    >
      <div className="task-bar-inner">
        {runningTasks.map((task) => (
          <div className="task-chip task-chip--running task-chip--wide" key={task.id}>
            <div className="task-chip-row" onClick={() => handleTaskClick(task)}>
              <Spinner animation="border" size="sm" className="task-chip-spinner" />
              <span className="task-chip-type">{typeLabel(task.type)}</span>
              {task.symbol && <span className="task-chip-symbol">{task.symbol}</span>}
              <div className="task-chip-progress-wrap">
                <ProgressBar
                  now={task.progress || 0}
                  animated
                  className="task-chip-progress"
                  variant="primary"
                />
              </div>
              <span className="task-chip-pct">{task.progress || 0}%</span>
              {task.stageMessage && (
                <span className="task-chip-stage d-none d-md-inline">
                  {task.stageMessage}
                </span>
              )}
            </div>
            <button
              type="button"
              className="task-chip-cancel"
              onClick={(e) => handleCancel(e, task)}
              title={isEnglish ? 'Cancel' : '取消'}
            >
              ×
            </button>
          </div>
        ))}

        {doneTasks.map((task) => (
          <div className="task-chip-group" key={task.id}>
            <button
              type="button"
              className={`task-chip task-chip--done ${task.seen ? '' : 'task-chip--unseen'}`}
              onClick={() => handleTaskClick(task)}
            >
              <Badge
                bg={task.status === 'done' ? 'success' : task.status === 'cancelled' ? 'secondary' : 'danger'}
                className="task-chip-badge"
              >
                {task.status === 'done'
                  ? (isEnglish ? 'Done' : '完成')
                  : task.status === 'cancelled'
                  ? (isEnglish ? 'Cancelled' : '已取消')
                  : (isEnglish ? 'Failed' : '失败')}
              </Badge>
              <span className="task-chip-type">{typeLabel(task.type)}</span>
              {task.symbol && <span className="task-chip-symbol">{task.symbol}</span>}
              {!task.seen && <span className="task-chip-dot" />}
            </button>
            <button
              type="button"
              className="task-chip-close"
              onClick={(e) => handleDismiss(e, task)}
              aria-label={isEnglish ? 'Dismiss' : '关闭'}
            >
              ×
            </button>
          </div>
        ))}

        {runningTasks.length > 0 && (
          <Badge bg="light" text="dark" className="task-bar-count">
            {runningTasks.length} {isEnglish ? 'running' : '运行中'}
          </Badge>
        )}
      </div>
    </div>
  );
};

export default PredictionTaskBar;
