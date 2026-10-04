import React, { createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef } from 'react';
import { getApiBaseUrl } from '../services/apiClient';

const PredictionTasksContext = createContext(null);

const TASK_EXPIRY_MS = 10 * 60 * 1000;
const POLL_INTERVAL_MS = 1200;
const STORAGE_KEY = 'prediction_tasks';

const loadFromStorage = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object') return parsed;
    }
  } catch { /* ignore */ }
  return {};
};

const saveToStorage = (tasks) => {
  try {
    const slim = {};
    Object.entries(tasks).forEach(([id, t]) => {
      slim[id] = {
        id: t.id, type: t.type, symbol: t.symbol, status: t.status,
        result: t.result, error: t.error, params: t.params, route: t.route,
        startedAt: t.startedAt, completedAt: t.completedAt, seen: t.seen,
      };
    });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(slim));
  } catch { /* ignore */ }
};

const reducer = (state, action) => {
  switch (action.type) {
    case 'HYDRATE':
      return { ...state, tasks: action.tasks };
    case 'START': {
      const now = Date.now();
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [action.id]: {
            id: action.id,
            type: action.taskType,
            symbol: action.symbol,
            status: 'running',
            result: null,
            error: null,
            params: action.params || {},
            route: action.route || '/investment',
            startedAt: now,
            completedAt: null,
            seen: false,
            progress: 0,
            stage: '',
            stageMessage: '',
            trainingDetails: null,
          },
        },
      };
    }
    case 'PROGRESS': {
      const existing = state.tasks[action.id];
      if (!existing) return state;
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [action.id]: {
            ...existing,
            status: 'running',
            progress: action.progress ?? existing.progress,
            stage: action.stage ?? existing.stage,
            stageMessage: action.stageMessage ?? existing.stageMessage,
            trainingDetails: action.trainingDetails ?? existing.trainingDetails,
          },
        },
      };
    }
    case 'COMPLETE': {
      const existing = state.tasks[action.id];
      if (!existing) return state;
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [action.id]: {
            ...existing,
            status: 'done',
            progress: 100,
            result: action.result,
            error: null,
            completedAt: Date.now(),
            seen: false,
          },
        },
      };
    }
    case 'FAIL': {
      const existing = state.tasks[action.id];
      if (!existing) return state;
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [action.id]: {
            ...existing,
            status: 'error',
            error: action.error || 'Unknown error',
            completedAt: Date.now(),
            seen: false,
          },
        },
      };
    }
    case 'CANCELLED': {
      const existing = state.tasks[action.id];
      if (!existing) return state;
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [action.id]: {
            ...existing,
            status: 'cancelled',
            completedAt: Date.now(),
            seen: true,
          },
        },
      };
    }
    case 'MARK_SEEN':
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [action.id]: { ...state.tasks[action.id], seen: true },
        },
      };
    case 'DISMISS': {
      const { [action.id]: _, ...rest } = state.tasks;
      return { ...state, tasks: rest };
    }
    case 'CLEANUP': {
      const now = Date.now();
      const cleaned = {};
      for (const [id, task] of Object.entries(state.tasks)) {
        if (task.status === 'running') cleaned[id] = task;
        else if (now - task.completedAt < TASK_EXPIRY_MS) cleaned[id] = task;
      }
      return { ...state, tasks: cleaned };
    }
    default:
      return state;
  }
};

let _nextId = 1;
const generateId = () => `task_${Date.now()}_${_nextId++}`;

export const PredictionTasksProvider = ({ children }) => {
  const [state, dispatch] = useReducer(reducer, { tasks: {} });
  const pollingRef = useRef(null);

  // Hydrate from localStorage on mount
  useEffect(() => {
    const stored = loadFromStorage();
    if (Object.keys(stored).length > 0) {
      dispatch({ type: 'HYDRATE', tasks: stored });
    }
  }, []);

  // Persist to localStorage on change
  useEffect(() => {
    saveToStorage(state.tasks);
  }, [state.tasks]);

  // Poll backend for progress on running tasks
  useEffect(() => {
    const runningIds = Object.values(state.tasks)
      .filter((t) => t.status === 'running')
      .map((t) => t.id);

    if (runningIds.length === 0) {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
      return;
    }

    if (!pollingRef.current) {
      pollingRef.current = setInterval(async () => {
        const ids = Object.values(state.tasks)
          .filter((t) => t.status === 'running')
          .map((t) => t.id)
          .slice(0, 4);

        for (const id of ids) {
          try {
            const base = getApiBaseUrl();
            const resp = await fetch(`${base}/api/tasks/status?task_id=${id}`);
            if (resp.ok) {
              const json = await resp.json();
              const t = json?.data;
              if (t) {
                if (t.status === 'done' || t.status === 'completed') {
                  dispatch({ type: 'COMPLETE', id, result: t.result });
                } else if (t.status === 'error') {
                  dispatch({ type: 'FAIL', id, error: t.error || 'Task failed' });
                } else if (t.status === 'cancelled') {
                  dispatch({ type: 'CANCELLED', id });
                } else if (t.status === 'running') {
                  dispatch({
                    type: 'PROGRESS',
                    id,
                    progress: t.progress || 0,
                    stage: t.stage || '',
                    stageMessage: t.stage_message || '',
                    trainingDetails: t.training_details || null,
                  });
                }
              }
            }
          } catch { /* poll errors are okay */ }
        }
      }, POLL_INTERVAL_MS);
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [state.tasks]);

  const findMatchingRunning = useCallback(
    (taskType, symbol) => {
      return Object.values(state.tasks).find(
        (t) => t.type === taskType && t.symbol === symbol && t.status === 'running',
      );
    },
    [state.tasks],
  );

  const startTask = useCallback(
    (info) => {
      const existing = findMatchingRunning(info.type, info.symbol);
      if (existing) return existing.id;
      const id = info.id || generateId();
      dispatch({
        type: 'START',
        id,
        taskType: info.type || 'unknown',
        symbol: info.symbol || '',
        params: info.params || {},
        route: info.route || '/investment',
      });
      return id;
    },
    [findMatchingRunning],
  );

  const updateProgress = useCallback((id, progress, stage, stageMessage) => {
    dispatch({ type: 'PROGRESS', id, progress, stage, stageMessage });
  }, []);

  const completeTask = useCallback((id, result) => {
    dispatch({ type: 'COMPLETE', id, result });
  }, []);

  const failTask = useCallback((id, error) => {
    dispatch({ type: 'FAIL', id, error: String(error || '') });
  }, []);

  const cancelTask = useCallback(async (id) => {
    try {
      const base = getApiBaseUrl();
      await fetch(`${base}/api/tasks/cancel?task_id=${id}`, { method: 'POST' });
    } catch { /* best effort */ }
    dispatch({ type: 'CANCELLED', id });
  }, []);

  const markSeen = useCallback((id) => {
    dispatch({ type: 'MARK_SEEN', id });
  }, []);

  const dismissTask = useCallback((id) => {
    dispatch({ type: 'DISMISS', id });
  }, []);

  const cleanup = useCallback(() => {
    dispatch({ type: 'CLEANUP' });
  }, []);

  const taskList = useMemo(() => {
    return Object.values(state.tasks).sort((a, b) => b.startedAt - a.startedAt);
  }, [state.tasks]);

  const runningCount = useMemo(() => {
    return taskList.filter((t) => t.status === 'running').length;
  }, [taskList]);

  const unseenDoneCount = useMemo(() => {
    return taskList.filter((t) => t.status === 'done' && !t.seen).length;
  }, [taskList]);

  const getLatestTask = useCallback(
    (taskType, symbol) => {
      const matches = taskList.filter((t) => t.type === taskType && t.symbol === symbol);
      return matches[0] || null;
    },
    [taskList],
  );

  const value = useMemo(
    () => ({
      tasks: state.tasks,
      taskList,
      runningCount,
      unseenDoneCount,
      startTask,
      updateProgress,
      completeTask,
      failTask,
      cancelTask,
      markSeen,
      dismissTask,
      cleanup,
      getLatestTask,
    }),
    [state.tasks, taskList, runningCount, unseenDoneCount, startTask, updateProgress, completeTask, failTask, cancelTask, markSeen, dismissTask, cleanup, getLatestTask],
  );

  return (
    <PredictionTasksContext.Provider value={value}>
      {children}
    </PredictionTasksContext.Provider>
  );
};

export const usePredictionTasks = () => {
  const ctx = useContext(PredictionTasksContext);
  if (!ctx) {
    throw new Error('usePredictionTasks must be used within PredictionTasksProvider');
  }
  return ctx;
};

export default PredictionTasksContext;
