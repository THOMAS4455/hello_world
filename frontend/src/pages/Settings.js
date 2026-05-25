import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Container, Form, Row, Spinner } from 'react-bootstrap';
import { useDispatch } from 'react-redux';
import { useAppI18n } from '../i18n';
import stockApiService from '../services/stockApi';
import { updateUser } from '../store/slices/authSlice';
import { setLanguage } from '../store/slices/uiSlice';

const defaultSettings = {
  theme: 'light',
  notifications: true,
  autoRefresh: true,
  refreshInterval: 30,
  language: 'zh-CN',
};

const Settings = () => {
  const dispatch = useDispatch();
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const [settings, setSettings] = useState(defaultSettings);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadProfile = async () => {
      setLoading(true);
      setError('');
      try {
        const user = await stockApiService.getUserProfile();
        const merged = {
          ...defaultSettings,
          ...(user?.settings || {}),
        };
        setSettings(merged);
        dispatch(updateUser({ settings: merged }));
        if (merged.language) {
          dispatch(setLanguage(merged.language));
        }
      } catch (err) {
        setError(err?.message || (isEnglish ? 'Failed to load settings.' : '加载设置失败。'));
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, [dispatch, isEnglish]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : type === 'number' ? Number(value || 0) : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    setError('');
    try {
      const payload = {
        ...settings,
        refreshInterval: Math.max(10, Math.min(300, Number(settings.refreshInterval) || 30)),
      };
      const user = await stockApiService.updateUserSettings(payload);
      setSettings({
        ...defaultSettings,
        ...(user?.settings || payload),
      });
      dispatch(updateUser(user || { settings: payload }));
      dispatch(setLanguage((user?.settings || payload).language || defaultSettings.language));
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err?.message || (isEnglish ? 'Failed to save settings.' : '保存设置失败。'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Container fluid className="py-4">
      <Row>
        <Col md={8} className="mx-auto">
          <Card>
            <Card.Header as="h4">{isEnglish ? 'System Settings' : '系统设置'}</Card.Header>
            <Card.Body>
              {loading ? (
                <div className="text-center py-4">
                  <Spinner animation="border" />
                </div>
              ) : (
                <>
                  {saved && (
                    <Alert variant="success" className="mb-3">
                      {isEnglish ? 'Settings saved successfully.' : '设置已保存。'}
                    </Alert>
                  )}
                  {error && (
                    <Alert variant="danger" className="mb-3">
                      {error}
                    </Alert>
                  )}

                  <Form onSubmit={handleSubmit}>
                    <Form.Group className="mb-3">
                      <Form.Label>{isEnglish ? 'Theme' : '主题'}</Form.Label>
                      <Form.Select name="theme" value={settings.theme} onChange={handleChange}>
                        <option value="light">{isEnglish ? 'Light' : '浅色'}</option>
                        <option value="dark">{isEnglish ? 'Dark' : '深色'}</option>
                        <option value="auto">{isEnglish ? 'Follow system' : '跟随系统'}</option>
                      </Form.Select>
                    </Form.Group>

                    <Form.Group className="mb-3">
                      <Form.Label>{isEnglish ? 'Language' : '语言'}</Form.Label>
                      <Form.Select name="language" value={settings.language} onChange={handleChange}>
                        <option value="zh-CN">简体中文</option>
                        <option value="en-US">English</option>
                      </Form.Select>
                    </Form.Group>

                    <Form.Group className="mb-3">
                      <Form.Check
                        type="checkbox"
                        name="notifications"
                        checked={Boolean(settings.notifications)}
                        onChange={handleChange}
                        label={isEnglish ? 'Enable notifications' : '启用通知'}
                      />
                    </Form.Group>

                    <Form.Group className="mb-3">
                      <Form.Check
                        type="checkbox"
                        name="autoRefresh"
                        checked={Boolean(settings.autoRefresh)}
                        onChange={handleChange}
                        label={isEnglish ? 'Auto refresh market data' : '自动刷新市场数据'}
                      />
                    </Form.Group>

                    <Form.Group className="mb-3">
                      <Form.Label>{isEnglish ? 'Refresh interval (seconds)' : '刷新间隔（秒）'}</Form.Label>
                      <Form.Control
                        type="number"
                        name="refreshInterval"
                        value={settings.refreshInterval}
                        onChange={handleChange}
                        min="10"
                        max="300"
                      />
                    </Form.Group>

                    <Button variant="primary" type="submit" disabled={saving}>
                      {saving ? (isEnglish ? 'Saving...' : '保存中...') : isEnglish ? 'Save Settings' : '保存设置'}
                    </Button>
                  </Form>
                </>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default Settings;
