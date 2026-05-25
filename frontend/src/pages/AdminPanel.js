import React, { useEffect, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  ButtonGroup,
  Card,
  Col,
  Form,
  Row,
  Spinner,
  Table,
} from 'react-bootstrap';
import { useDispatch, useSelector } from 'react-redux';
import { useAppI18n } from '../i18n';
import {
  useGetAdminDatabaseInfoQuery,
  useGetAdminSystemConfigQuery,
  useGetAdminUsersQuery,
  useUpdateAdminSystemConfigMutation,
  useGetAdminFeatureHistoryStatusQuery,
  useBackfillAdminFeatureHistoryMutation,
} from '../services/apiService';
import { setLanguage } from '../store/slices/uiSlice';
import ServiceStatus from '../components/ServiceStatus';
import '../styles/AdminPanel.css';

const AdminPanel = () => {
  const dispatch = useDispatch();
  const { language, t } = useAppI18n();
  const roles = useSelector((state) => state?.auth?.roles || []);
  const isAdmin = Array.isArray(roles) && roles.some((role) => String(role).toLowerCase() === 'admin');

  const { data: usersResp, isLoading: usersLoading, error: usersError, refetch: refetchUsers } =
    useGetAdminUsersQuery(undefined, { skip: !isAdmin });
  const { data: dbResp, isLoading: dbLoading, error: dbError, refetch: refetchDb } =
    useGetAdminDatabaseInfoQuery(undefined, { skip: !isAdmin });
  const {
    data: cfgResp,
    isLoading: cfgLoading,
    error: cfgError,
    refetch: refetchCfg,
  } = useGetAdminSystemConfigQuery(undefined, { skip: !isAdmin });
  const [updateConfig, { isLoading: savingConfig }] = useUpdateAdminSystemConfigMutation();
  const {
    data: featureHistoryResp,
    isLoading: featureHistoryLoading,
    refetch: refetchFeatureHistory,
  } = useGetAdminFeatureHistoryStatusQuery(undefined, { skip: !isAdmin });
  const [backfillFeatureHistory, { isLoading: backfillingFeatureHistory }] =
    useBackfillAdminFeatureHistoryMutation();

  const [aiForm, setAiForm] = useState({
    api_key: '',
    api_url: '',
    model: '',
    timeout: 30,
    retry_count: 3,
    retry_delay: 1,
    max_tokens: 2000,
    temperature: 0.7,
  });
  const [dataSourceForm, setDataSourceForm] = useState({ stock_source: 'aggregate_realtime' });
  const [saveMsg, setSaveMsg] = useState('');
  const [saveErr, setSaveErr] = useState('');
  const [featureForm, setFeatureForm] = useState({
    days: 90,
    news_limit: 300,
    fill_sentiment: true,
    fill_breadth: true,
    overwrite: false,
  });
  const [featureMsg, setFeatureMsg] = useState('');
  const [featureErr, setFeatureErr] = useState('');

  useEffect(() => {
    const ai = cfgResp?.data?.ai || {};
    const ds = cfgResp?.data?.data_source || {};
    setAiForm((prev) => ({
      ...prev,
      api_key: '',
      api_url: ai.api_url || prev.api_url,
      model: ai.model || prev.model,
      timeout: Number(ai.timeout || prev.timeout),
      retry_count: Number(ai.retry_count || prev.retry_count),
      retry_delay: Number(ai.retry_delay || prev.retry_delay),
      max_tokens: Number(ai.max_tokens || prev.max_tokens),
      temperature: Number(ai.temperature || prev.temperature),
    }));
    setDataSourceForm({
      stock_source: ds.stock_source || 'aggregate_realtime',
    });
  }, [cfgResp]);

  if (!isAdmin) {
    return (
      <div className="analysis-page admin-panel-page">
        <Alert variant="danger">{t('adminNoAccess')}</Alert>
      </div>
    );
  }

  const users = usersResp?.data?.users || [];
  const dbInfo = dbResp?.data || {};
  const files = dbInfo?.files || [];
  const availableSources = cfgResp?.data?.data_source?.available_stock_sources || [];
  const sourceHealth = cfgResp?.data?.data_source?.source_health || {};
  const refreshStatus = cfgResp?.data?.data_source?.refresh_status || {};
  const sourceHealthRows = Object.entries(sourceHealth).sort(([a], [b]) => a.localeCompare(b));
  const aiMasked = cfgResp?.data?.ai?.api_key_masked || '';

  const featureStatus = featureHistoryResp?.data || {};
  const onRunFeatureBackfill = async () => {
    setFeatureMsg('');
    setFeatureErr('');
    try {
      const resp = await backfillFeatureHistory(featureForm).unwrap();
      if (!resp?.success) {
        throw new Error(resp?.message || t('adminFeatureBackfillFailed'));
      }
      const written = (resp?.data?.sentiment?.written || 0) + (resp?.data?.breadth?.written || 0);
      setFeatureMsg(`${t('adminFeatureBackfillDone')} (+${written})`);
      refetchFeatureHistory();
    } catch (err) {
      setFeatureErr(err?.data?.message || err?.message || t('adminFeatureBackfillFailed'));
    }
  };

  const onSaveSystemConfig = async () => {
    setSaveMsg('');
    setSaveErr('');
    try {
      const payload = {
        ai: {
          ...aiForm,
        },
        data_source: {
          stock_source: dataSourceForm.stock_source,
        },
      };

      if (!payload.ai.api_key) {
        delete payload.ai.api_key;
      }

      const resp = await updateConfig(payload).unwrap();
      if (!resp?.success) {
        throw new Error(resp?.message || t('adminSaveFailed'));
      }
      setSaveMsg(t('adminSaveSuccess'));
      refetchCfg();
      refetchDb();
    } catch (err) {
      setSaveErr(err?.data?.message || err?.message || t('adminSaveFailed'));
    }
  };

  return (
    <div className="analysis-page admin-panel-page">
      <ServiceStatus />
      <h1 className="mb-3">{t('adminTitle')}</h1>

      <div className="d-flex gap-2 mb-3 admin-kpi-row">
        <Badge bg="dark">{t('adminBadge')}</Badge>
        <Badge bg="secondary">
          {t('adminTotalUsers')}: {usersResp?.data?.total ?? 0}
        </Badge>
      </div>

      <Card className="mb-3 admin-card">
        <Card.Header className="d-flex justify-content-between align-items-center">
          <span>{t('adminFeatureHistory')}</span>
          <Button size="sm" variant="outline-primary" onClick={refetchFeatureHistory}>
            {t('adminRefresh')}
          </Button>
        </Card.Header>
        <Card.Body>
          <p className="small text-muted">{t('adminFeatureHistoryHelp')}</p>
          {featureHistoryLoading ? (
            <Spinner animation="border" size="sm" />
          ) : (
            <div className="small text-muted mb-3">
              {t('adminFeatureBreadthCount')}: {featureStatus.breadth_days ?? 0}
              {featureStatus.breadth_range?.start ? ` (${featureStatus.breadth_range.start} ~ ${featureStatus.breadth_range.end})` : ''}
              {' · '}
              {t('adminFeatureSentimentCount')}: {featureStatus.sentiment_days ?? 0}
              {featureStatus.sentiment_range?.start ? ` (${featureStatus.sentiment_range.start} ~ ${featureStatus.sentiment_range.end})` : ''}
            </div>
          )}
          <Row className="g-2 mb-2">
            <Col md={3}>
              <Form.Group>
                <Form.Label>{t('adminFeatureBreadthDays')}</Form.Label>
                <Form.Control
                  type="number"
                  min={7}
                  max={365}
                  value={featureForm.days}
                  onChange={(e) => setFeatureForm((p) => ({ ...p, days: Number(e.target.value) }))}
                />
              </Form.Group>
            </Col>
            <Col md={3}>
              <Form.Group>
                <Form.Label>{t('adminFeatureSentimentNews')}</Form.Label>
                <Form.Control
                  type="number"
                  min={50}
                  max={500}
                  value={featureForm.news_limit}
                  onChange={(e) => setFeatureForm((p) => ({ ...p, news_limit: Number(e.target.value) }))}
                />
              </Form.Group>
            </Col>
            <Col md={6} className="d-flex align-items-end gap-3 flex-wrap">
              <Form.Check
                type="switch"
                id="fill-sentiment"
                label={t('adminFeatureFillSentiment')}
                checked={featureForm.fill_sentiment}
                onChange={(e) => setFeatureForm((p) => ({ ...p, fill_sentiment: e.target.checked }))}
              />
              <Form.Check
                type="switch"
                id="fill-breadth"
                label={t('adminFeatureFillBreadth')}
                checked={featureForm.fill_breadth}
                onChange={(e) => setFeatureForm((p) => ({ ...p, fill_breadth: e.target.checked }))}
              />
              <Form.Check
                type="switch"
                id="overwrite-feature"
                label={t('adminFeatureOverwrite')}
                checked={featureForm.overwrite}
                onChange={(e) => setFeatureForm((p) => ({ ...p, overwrite: e.target.checked }))}
              />
            </Col>
          </Row>
          {featureMsg ? <Alert variant="success">{featureMsg}</Alert> : null}
          {featureErr ? <Alert variant="danger">{featureErr}</Alert> : null}
          <Button
            variant="primary"
            disabled={backfillingFeatureHistory}
            onClick={onRunFeatureBackfill}
          >
            {backfillingFeatureHistory ? t('adminFeatureBackfilling') : t('adminFeatureRunBackfill')}
          </Button>
        </Card.Body>
      </Card>

      <Row className="g-3 mb-3 admin-top-grid">
        <Col lg={4}>
          <Card className="h-100 admin-card">
            <Card.Header>{t('adminLanguageCard')}</Card.Header>
            <Card.Body>
              <div className="small text-muted mb-2">{t('adminLanguageHelp')}</div>
              <Form.Group>
                <Form.Label>{t('adminLanguageLabel')}</Form.Label>
                <ButtonGroup className="w-100">
                  <Button
                    variant={language === 'zh-CN' ? 'primary' : 'outline-primary'}
                    onClick={() => dispatch(setLanguage('zh-CN'))}
                  >
                    {t('adminLanguageZh')}
                  </Button>
                  <Button
                    variant={language === 'en-US' ? 'primary' : 'outline-primary'}
                    onClick={() => dispatch(setLanguage('en-US'))}
                  >
                    {t('adminLanguageEn')}
                  </Button>
                </ButtonGroup>
              </Form.Group>
            </Card.Body>
          </Card>
        </Col>

        <Col lg={4}>
          <Card className="h-100 admin-card">
            <Card.Header>{t('adminAiConfig')}</Card.Header>
            <Card.Body>
              {cfgLoading ? (
                <Spinner animation="border" size="sm" />
              ) : cfgError ? (
                <Alert variant="danger">
                  {cfgError?.data?.message || cfgError?.error || t('adminLoadingConfigFailed')}
                </Alert>
              ) : (
                <>
                  <div className="small text-muted mb-2">
                    {t('adminCurrentApiKey')}: {aiMasked || t('adminNotConfigured')}
                  </div>
                  <Form>
                    <Form.Group className="mb-2">
                      <Form.Label>{t('adminNewApiKey')}</Form.Label>
                      <Form.Control
                        type="password"
                        value={aiForm.api_key}
                        onChange={(e) => setAiForm((prev) => ({ ...prev, api_key: e.target.value }))}
                        placeholder={t('adminNewApiKeyPlaceholder')}
                      />
                    </Form.Group>
                    <Form.Group className="mb-2">
                      <Form.Label>{t('adminApiUrl')}</Form.Label>
                      <Form.Control
                        value={aiForm.api_url}
                        onChange={(e) => setAiForm((prev) => ({ ...prev, api_url: e.target.value }))}
                      />
                    </Form.Group>
                    <Row className="g-2">
                      <Col md={6}>
                        <Form.Group className="mb-2">
                          <Form.Label>{t('adminModel')}</Form.Label>
                          <Form.Control
                            value={aiForm.model}
                            onChange={(e) => setAiForm((prev) => ({ ...prev, model: e.target.value }))}
                          />
                        </Form.Group>
                      </Col>
                      <Col md={6}>
                        <Form.Group className="mb-2">
                          <Form.Label>{t('adminTimeout')}</Form.Label>
                          <Form.Control
                            type="number"
                            value={aiForm.timeout}
                            onChange={(e) =>
                              setAiForm((prev) => ({ ...prev, timeout: Number(e.target.value || 30) }))
                            }
                          />
                        </Form.Group>
                      </Col>
                    </Row>
                  </Form>
                </>
              )}
            </Card.Body>
          </Card>
        </Col>

        <Col lg={4}>
          <Card className="h-100 admin-card">
            <Card.Header>{t('adminDataSource')}</Card.Header>
            <Card.Body>
              {cfgLoading ? (
                <Spinner animation="border" size="sm" />
              ) : (
                <Form>
                  <Form.Group className="mb-2">
                    <Form.Label>{t('adminStockSource')}</Form.Label>
                    <Form.Select
                      value={dataSourceForm.stock_source}
                      onChange={(e) =>
                        setDataSourceForm((prev) => ({ ...prev, stock_source: e.target.value }))
                      }
                    >
                      {availableSources.map((item) => (
                        <option key={item.code} value={item.code}>
                          {item.code} - {item.name}
                        </option>
                      ))}
                    </Form.Select>
                  </Form.Group>
                  <div className="small text-muted">{t('adminDataSourceHelp')}</div>
                </Form>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {(saveMsg || saveErr) && (
        <Alert variant={saveErr ? 'danger' : 'success'}>{saveErr || saveMsg}</Alert>
      )}

      <div className="mb-3 d-flex gap-2 admin-actions">
        <Button onClick={onSaveSystemConfig} disabled={savingConfig}>
          {savingConfig ? t('adminSaving') : t('adminSaveConfig')}
        </Button>
        <Button variant="outline-secondary" onClick={refetchCfg}>
          {t('adminRefreshConfig')}
        </Button>
      </div>

      {sourceHealthRows.length > 0 && (
        <Card className="mb-3 admin-card">
          <Card.Header>{t('adminSourceHealth')}</Card.Header>
          <Card.Body className="p-0">
            <div className="small text-muted px-3 pt-3 pb-2">
              {t('adminLastSuccess')}: {refreshStatus.last_success_at || '-'}
              {' · '}
              {t('adminLastError')}: {refreshStatus.last_error || '-'}
              {' · '}
              {t('adminHealthySources')}:{' '}
              {sourceHealthRows.filter(([, item]) => item?.success).length}/{sourceHealthRows.length}
            </div>
            <div className="table-responsive">
              <Table striped bordered hover size="sm" className="mb-0">
                <thead>
                  <tr>
                    <th>{t('dashboardSourceName')}</th>
                    <th>{t('dashboardSourceStatus')}</th>
                    <th>{t('dashboardSourceLatency')}</th>
                    <th>{t('dashboardSourceItems')}</th>
                  </tr>
                </thead>
                <tbody>
                  {sourceHealthRows.map(([source, item]) => (
                    <tr key={source}>
                      <td>{source}</td>
                      <td>
                        <Badge bg={item?.success ? 'success' : 'danger'}>
                          {item?.success ? t('dashboardHealthy') : t('dashboardUnhealthy')}
                        </Badge>
                      </td>
                      <td>{item?.latency_ms ?? '-'}</td>
                      <td>{item?.item_count ?? '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </div>
          </Card.Body>
        </Card>
      )}

      <Row className="g-3">
        <Col lg={7}>
          <Card className="admin-card">
            <Card.Header className="d-flex justify-content-between align-items-center">
              <span>{t('adminUsers')}</span>
              <Button size="sm" variant="outline-primary" onClick={refetchUsers}>
                {t('adminRefresh')}
              </Button>
            </Card.Header>
            <Card.Body>
              {usersLoading ? (
                <Spinner animation="border" size="sm" />
              ) : usersError ? (
                <Alert variant="danger">
                  {usersError?.data?.message || usersError?.error || t('adminLoadingUsersFailed')}
                </Alert>
              ) : (
                <Table hover size="sm" className="admin-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>{t('adminUsername')}</th>
                      <th>{t('adminEmail')}</th>
                      <th>{t('adminRole')}</th>
                      <th>{t('adminRegisteredAt')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user) => (
                      <tr key={user.id}>
                        <td>{user.id}</td>
                        <td>{user.username}</td>
                        <td>{user.email}</td>
                        <td>{Array.isArray(user.roles) ? user.roles.join(', ') : 'user'}</td>
                        <td>{user.created_at || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card.Body>
          </Card>
        </Col>

        <Col lg={5}>
          <Card className="admin-card">
            <Card.Header className="d-flex justify-content-between align-items-center">
              <span>{t('adminDatabaseInfo')}</span>
              <Button size="sm" variant="outline-primary" onClick={refetchDb}>
                {t('adminRefresh')}
              </Button>
            </Card.Header>
            <Card.Body>
              {dbLoading ? (
                <Spinner animation="border" size="sm" />
              ) : dbError ? (
                <Alert variant="danger">
                  {dbError?.data?.message || dbError?.error || t('adminLoadingDatabaseFailed')}
                </Alert>
              ) : (
                <>
                  <div className="small text-muted mb-2">
                    {t('adminStorageType')}: {dbInfo.storage_type || '-'}
                  </div>
                  <div className="small text-muted mb-3">
                    {t('adminDataDir')}: {dbInfo.data_dir || '-'}
                  </div>
                  <Table bordered size="sm" className="admin-table">
                    <thead>
                      <tr>
                        <th>{t('adminFileName')}</th>
                        <th>{t('adminFileSize')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {files.map((file) => (
                        <tr key={file.path}>
                          <td>{file.name}</td>
                          <td>{file.size_bytes}</td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AdminPanel;
