import React, { useEffect, useMemo, useState } from 'react';
import { Badge, Button, Card, Spinner } from 'react-bootstrap';
import { useAppI18n } from '../i18n';
import '../styles/ServiceStatus.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const StatusRow = ({ label, status, detail, t }) => {
  const badge = useMemo(() => {
    if (status === 'online') return { bg: 'success', text: t('serviceOnline') };
    if (status === 'offline') return { bg: 'danger', text: t('serviceOffline') };
    return { bg: 'secondary', text: t('serviceChecking') };
  }, [status, t]);

  return (
    <div className="status-row">
      <div>
        <div className="status-label">{label}</div>
        <div className="status-detail">{detail}</div>
      </div>
      <Badge bg={badge.bg}>{badge.text}</Badge>
    </div>
  );
};

const ServiceStatus = () => {
  const { t } = useAppI18n();
  const [expanded, setExpanded] = useState(false);
  const [dataStatus, setDataStatus] = useState('checking');
  const [aiStatus, setAiStatus] = useState('checking');
  const [predictionStatus, setPredictionStatus] = useState('checking');
  const [dataInfo, setDataInfo] = useState(null);
  const [aiInfo, setAiInfo] = useState(null);
  const [predictionInfo, setPredictionInfo] = useState(null);
  const [realtimeInfo, setRealtimeInfo] = useState(null);
  const [lastCheck, setLastCheck] = useState(null);
  const [checking, setChecking] = useState(false);

  const checkServices = async () => {
    setChecking(true);
    try {
      const healthResp = await fetch(`${API_BASE_URL}/health`);
      if (healthResp.ok) {
        const health = await healthResp.json();
        setDataInfo(health);
        setDataStatus('online');
      } else {
        setDataStatus('offline');
      }
    } catch {
      setDataStatus('offline');
    }

    try {
      const systemResp = await fetch(`${API_BASE_URL}/api/system/health`);
      if (systemResp.ok) {
        const system = await systemResp.json();
        const data = system?.data?.components?.data_service || null;
        const ai = system?.data?.components?.ai_service || null;
        const prediction = system?.data?.components?.prediction_service || null;
        setDataInfo(data);
        setAiInfo(ai);
        setPredictionInfo(prediction);
        setDataStatus(data?.status === 'healthy' ? 'online' : 'offline');
        setAiStatus(ai?.status === 'online' ? 'online' : 'offline');
        setPredictionStatus(prediction?.status === 'healthy' ? 'online' : 'offline');
      } else {
        setDataStatus('offline');
        setAiStatus('offline');
        setPredictionStatus('offline');
      }
    } catch {
      setDataStatus('offline');
      setAiStatus('offline');
      setPredictionStatus('offline');
    }

    try {
      const realtimeResp = await fetch(`${API_BASE_URL}/api/stocks/realtime`);
      if (realtimeResp.ok) {
        const realtime = await realtimeResp.json();
        setRealtimeInfo(realtime?.data || null);
      } else {
        setRealtimeInfo(null);
      }
    } catch {
      setRealtimeInfo(null);
    }

    setLastCheck(new Date());
    setChecking(false);
  };

  useEffect(() => {
    checkServices();
    const timer = setInterval(checkServices, 30000);
    return () => clearInterval(timer);
  }, []);

  const overallHealthy = dataStatus === 'online' && aiStatus === 'online' && predictionStatus === 'online';
  const freshness = realtimeInfo?.freshness || {};
  const sourceHealth = freshness?.source_health || {};
  const sourceRows = Object.values(sourceHealth).slice(0, 3);
  const freshnessLabel = (() => {
    if (!freshness?.source) return 'No realtime snapshot';
    if (freshness?.is_live) return `Live | ${freshness.source}`;
    const staleSeconds = Number(freshness?.stale_seconds || 0);
    return `Stale ${Math.round(staleSeconds)}s | ${freshness.source}`;
  })();

  return (
    <div className="service-fab-wrap">
      <button
        type="button"
        className={`service-fab ${overallHealthy ? 'ok' : 'warn'}`}
        onClick={() => setExpanded((value) => !value)}
      >
        <span className="service-fab-dot" />
        {t('serviceSystemStatus')}
      </button>

      {expanded && (
        <Card className="service-fab-panel">
          <Card.Body>
            <div className="service-fab-head">
              <div className="service-fab-title">{t('servicePanelTitle')}</div>
              <Button size="sm" variant="outline-secondary" onClick={checkServices} disabled={checking}>
                {checking ? (
                  <>
                    <Spinner animation="border" size="sm" className="me-1" />
                    {t('serviceChecking')}
                  </>
                ) : (
                  t('serviceRefresh')
                )}
              </Button>
            </div>

            <StatusRow
              label={t('serviceDataService')}
              status={dataStatus}
              detail={`${freshnessLabel} | ${dataInfo?.runtime?.refresh_status?.last_success_source || 'no-source'}`}
              t={t}
            />
            <StatusRow
              label={t('serviceAiService')}
              status={aiStatus}
              detail={`${t('serviceModel')} ${aiInfo?.model || 'N/A'}`}
              t={t}
            />
            <StatusRow
              label="Prediction Service"
              status={predictionStatus}
              detail={`${predictionInfo?.runtime?.available_models?.length || 0} models`}
              t={t}
            />

            {sourceRows.length > 0 && (
              <div className="status-row">
                <div>
                  <div className="status-label">Data Sources</div>
                  <div className="status-detail">
                    {sourceRows
                      .map((item) => {
                        const state = item?.success ? 'ok' : 'fail';
                        const latency = item?.latency_ms ? `${Math.round(item.latency_ms)}ms` : 'n/a';
                        return `${item?.source || 'unknown'}:${state}:${latency}`;
                      })
                      .join(' | ')}
                  </div>
                </div>
                <Badge bg={freshness?.is_live ? 'success' : 'warning'}>
                  {freshness?.quote_timestamp || 'no-ts'}
                </Badge>
              </div>
            )}

            <div className="service-fab-time">
              {t('serviceLastCheck')}: {lastCheck ? lastCheck.toLocaleTimeString() : t('serviceNeverChecked')}
            </div>
          </Card.Body>
        </Card>
      )}
    </div>
  );
};

export default ServiceStatus;
