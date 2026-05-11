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
  const [dataInfo, setDataInfo] = useState(null);
  const [aiInfo, setAiInfo] = useState(null);
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
        const ai = system?.data?.components?.ai_service || null;
        setAiInfo(ai);
        setAiStatus(ai?.status === 'online' ? 'online' : 'offline');
      } else {
        setAiStatus('offline');
      }
    } catch {
      setAiStatus('offline');
    }

    setLastCheck(new Date());
    setChecking(false);
  };

  useEffect(() => {
    checkServices();
    const timer = setInterval(checkServices, 30000);
    return () => clearInterval(timer);
  }, []);

  const overallHealthy = dataStatus === 'online' && aiStatus === 'online';

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
              detail={`${t('serviceVersion')} ${dataInfo?.version || 'N/A'}`}
              t={t}
            />
            <StatusRow
              label={t('serviceAiService')}
              status={aiStatus}
              detail={`${t('serviceModel')} ${aiInfo?.model || 'N/A'}`}
              t={t}
            />

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
