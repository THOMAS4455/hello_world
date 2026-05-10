import React, { useState } from 'react';
import { Container, Row, Col, Card, Form, Button, Alert } from 'react-bootstrap';
import { useAppI18n } from '../i18n';

const Settings = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const [settings, setSettings] = useState({
    theme: 'light',
    notifications: true,
    autoRefresh: true,
    refreshInterval: 30,
  });
  const [saved, setSaved] = useState(false);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setSettings((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    localStorage.setItem('userSettings', JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <Container fluid className="py-4">
      <Row>
        <Col md={8} className="mx-auto">
          <Card>
            <Card.Header as="h4">{isEnglish ? 'System Settings' : '系统设置'}</Card.Header>
            <Card.Body>
              {saved && (
                <Alert variant="success" className="mb-3">
                  {isEnglish ? 'Settings saved successfully.' : '设置已保存成功！'}
                </Alert>
              )}

              <Form onSubmit={handleSubmit}>
                <Form.Group className="mb-3">
                  <Form.Label>{isEnglish ? 'Theme' : '主题设置'}</Form.Label>
                  <Form.Select name="theme" value={settings.theme} onChange={handleChange}>
                    <option value="light">{isEnglish ? 'Light' : '浅色主题'}</option>
                    <option value="dark">{isEnglish ? 'Dark' : '深色主题'}</option>
                    <option value="auto">{isEnglish ? 'Follow system' : '跟随系统'}</option>
                  </Form.Select>
                </Form.Group>

                <Form.Group className="mb-3">
                  <Form.Check
                    type="checkbox"
                    name="notifications"
                    checked={settings.notifications}
                    onChange={handleChange}
                    label={isEnglish ? 'Enable notifications' : '启用通知提醒'}
                  />
                </Form.Group>

                <Form.Group className="mb-3">
                  <Form.Check
                    type="checkbox"
                    name="autoRefresh"
                    checked={settings.autoRefresh}
                    onChange={handleChange}
                    label={isEnglish ? 'Auto refresh market data' : '自动刷新数据'}
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

                <Button variant="primary" type="submit">
                  {isEnglish ? 'Save Settings' : '保存设置'}
                </Button>
              </Form>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default Settings;
