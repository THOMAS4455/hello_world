import React, { useMemo, useState } from 'react';
import { Accordion, Badge, Button, Card, Col, Nav, Row, Tab } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { getGuideContent } from '../content/guideContent';
import { useAppI18n } from '../i18n';
import PageLogo from '../components/PageLogo';
import '../styles/Guide.css';

const Guide = () => {
  const { language, t } = useAppI18n();
  const navigate = useNavigate();
  const content = useMemo(() => getGuideContent(language), [language]);
  const [activeTab, setActiveTab] = useState('start');

  return (
    <div className="analysis-page guide-page">
      <section className="guide-hero mb-4">
        <PageLogo
          title={content.heroTitle}
          subtitle={content.heroSubtitle}
          glyph="G"
          tone="blue"
        />
        <p className="guide-hero-desc">{content.heroDesc}</p>
      </section>

      <Tab.Container activeKey={activeTab} onSelect={(key) => key && setActiveTab(key)}>
        <Nav variant="pills" className="guide-tabs mb-4 flex-wrap">
          <Nav.Item>
            <Nav.Link eventKey="start">{content.tabs.start}</Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link eventKey="features">{content.tabs.features}</Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link eventKey="prediction">{content.tabs.prediction}</Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link eventKey="data">{content.tabs.data}</Nav.Link>
          </Nav.Item>
        </Nav>

        <Tab.Content>
          <Tab.Pane eventKey="start">
            <Card className="guide-card mb-3">
              <Card.Body>
                <h2 className="guide-section-title">{content.start.title}</h2>
                <div className="guide-steps">
                  {content.start.steps.map((step) => (
                    <div className="guide-step" key={step.title}>
                      <div className="guide-step-head">
                        <h3>{step.title}</h3>
                        <Button size="sm" variant="outline-primary" onClick={() => navigate(step.path)}>
                          {step.pathLabel}
                        </Button>
                      </div>
                      <p>{step.body}</p>
                    </div>
                  ))}
                </div>
                <div className="guide-tips mt-4">
                  <h4>{language === 'en-US' ? 'Tips' : '使用提示'}</h4>
                  <ul>
                    {content.start.tips.map((tip) => (
                      <li key={tip}>{tip}</li>
                    ))}
                  </ul>
                </div>
              </Card.Body>
            </Card>
          </Tab.Pane>

          <Tab.Pane eventKey="features">
            <Card className="guide-card mb-3">
              <Card.Body>
                <h2 className="guide-section-title">{content.features.title}</h2>
                <Accordion alwaysOpen>
                  {content.features.items.map((item, index) => (
                    <Accordion.Item eventKey={String(index)} key={item.name}>
                      <Accordion.Header>
                        <span className="guide-feature-name">{item.name}</span>
                        {item.needAuth ? (
                          <Badge bg="secondary" className="ms-2">
                            {t('guideNeedLogin', 'Login required')}
                          </Badge>
                        ) : (
                          <Badge bg="success" className="ms-2">
                            {t('guidePublic', 'Public')}
                          </Badge>
                        )}
                      </Accordion.Header>
                      <Accordion.Body>
                        <p className="guide-feature-summary">{item.summary}</p>
                        <ol className="guide-how-list">
                          {item.how.map((line) => (
                            <li key={line}>{line}</li>
                          ))}
                        </ol>
                        <Button size="sm" variant="primary" onClick={() => navigate(item.path)}>
                          {language === 'en-US' ? 'Open module' : '打开模块'}
                        </Button>
                      </Accordion.Body>
                    </Accordion.Item>
                  ))}
                </Accordion>
              </Card.Body>
            </Card>
          </Tab.Pane>

          <Tab.Pane eventKey="prediction">
            <Row className="g-3">
              <Col lg={8}>
                <Card className="guide-card h-100">
                  <Card.Body>
                    <h2 className="guide-section-title">{content.prediction.title}</h2>
                    <p className="guide-lead">{content.prediction.intro}</p>

                    <h3 className="guide-subtitle">{content.prediction.layersTitle}</h3>
                    <div className="guide-layer-grid">
                      {content.prediction.layers.map((layer) => (
                        <div className="guide-layer-card" key={layer.name}>
                          <strong>{layer.name}</strong>
                          <p>{layer.desc}</p>
                        </div>
                      ))}
                    </div>
                    <p className="guide-note">{content.prediction.ensemble}</p>

                    <h3 className="guide-subtitle">{content.prediction.featuresTitle}</h3>
                    <ul>
                      {content.prediction.features.map((f) => (
                        <li key={f}>{f}</li>
                      ))}
                    </ul>

                    <h3 className="guide-subtitle">{content.prediction.paramsTitle}</h3>
                    <div className="guide-param-table">
                      {content.prediction.params.map((p) => (
                        <div className="guide-param-row" key={p.key}>
                          <code>{p.key}</code>
                          <span>{p.desc}</span>
                        </div>
                      ))}
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              <Col lg={4}>
                <Card className="guide-card guide-warning-card h-100">
                  <Card.Body>
                    <h3 className="guide-subtitle">{content.prediction.limitsTitle}</h3>
                    <ul className="guide-warning-list">
                      {content.prediction.limits.map((line) => (
                        <li key={line}>{line}</li>
                      ))}
                    </ul>
                    <Button variant="outline-light" className="mt-3" onClick={() => navigate('/predictions')}>
                      {language === 'en-US' ? 'Try a forecast' : '去试一次预测'}
                    </Button>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          </Tab.Pane>

          <Tab.Pane eventKey="data">
            <Card className="guide-card">
              <Card.Body>
                <h2 className="guide-section-title">{content.data.title}</h2>
                <Accordion>
                  {content.data.items.map((item, index) => (
                    <Accordion.Item eventKey={String(index)} key={item.q}>
                      <Accordion.Header>{item.q}</Accordion.Header>
                      <Accordion.Body>{item.a}</Accordion.Body>
                    </Accordion.Item>
                  ))}
                </Accordion>
              </Card.Body>
            </Card>
          </Tab.Pane>
        </Tab.Content>
      </Tab.Container>
    </div>
  );
};

export default Guide;
