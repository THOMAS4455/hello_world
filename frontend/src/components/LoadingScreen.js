import React from 'react';
import { Spinner, Container, Row, Col } from 'react-bootstrap';
import { useAppI18n } from '../i18n';
import './LoadingScreen.css';

const LoadingScreen = ({ message, showLogo = true }) => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';

  return (
    <div className="loading-screen">
      <Container className="h-100 d-flex align-items-center justify-content-center">
        <Row className="text-center">
          <Col>
            {showLogo && (
              <div className="mb-4">
                <div className="logo-container">
                  <div className="logo-icon" aria-hidden>A</div>
                  <h1 className="logo-text">AlphaScope</h1>
                </div>
              </div>
            )}

            <div className="loading-content">
              <Spinner animation="border" variant="primary" className="mb-3" />
              <p className="loading-message">{message || (isEnglish ? 'Loading...' : '正在加载...')}</p>

              <div className="loading-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>

            <div className="loading-tips mt-4">
              <small className="text-muted">
                {isEnglish
                  ? 'Tip: The system is getting ready. Please wait a moment.'
                  : '提示：系统正在准备中，请稍候片刻...'}
              </small>
            </div>
          </Col>
        </Row>
      </Container>
    </div>
  );
};

export default LoadingScreen;
