import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Alert, Button, Card, Col, Container, Form, Row, Spinner } from 'react-bootstrap';
import { useDispatch } from 'react-redux';
import { useAppI18n } from '../i18n';
import PageLogo from '../components/PageLogo';
import { useLoginMutation } from '../services/apiService';
import { loginFailure, loginStart, loginSuccess } from '../store/slices/authSlice';
import '../styles/AuthPages.css';

const Login = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = location.state?.from?.pathname || '/';
  const [formData, setFormData] = useState({ username: '', password: '' });
  const [localError, setLocalError] = useState('');
  const [login, { isLoading }] = useLoginMutation();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError('');

    const username = formData.username.trim();
    const password = formData.password;
    if (!username || !password) {
      setLocalError(isEnglish ? 'Please enter both username and password.' : '请输入用户名和密码。');
      return;
    }

    try {
      dispatch(loginStart());
      const response = await login({ username, password }).unwrap();
      if (!response?.success || !response?.data) {
        throw new Error(response?.message || (isEnglish ? 'Login failed.' : '登录失败。'));
      }
      dispatch(loginSuccess(response.data));
      navigate(redirectTo, { replace: true });
    } catch (err) {
      const message =
        err?.data?.message ||
        err?.message ||
        (isEnglish ? 'Login failed. Please try again later.' : '登录失败，请稍后再试。');
      dispatch(loginFailure(message));
      setLocalError(message);
    }
  };

  return (
    <div className="auth-page auth-login-page">
      <Container fluid="xl" className="auth-container">
        <Row className="g-4 align-items-stretch">
          <Col lg={6} className="d-flex">
            <Card className="auth-side-card w-100">
              <Card.Body>
                <PageLogo title="AlphaScope" subtitle="Secure Sign-in" glyph="L" tone="orange" compact />
                <div className="auth-side-tag">
                  {isEnglish ? 'Intelligent Research Platform' : '智能投研平台'}
                </div>
                <h1 className="auth-side-title">{isEnglish ? 'Welcome back' : '欢迎回来'}</h1>
                <p className="auth-side-text">
                  {isEnglish
                    ? 'After logging in, you can continue using forecasts, backtests, and sentiment tools while keeping your personal settings synced.'
                    : '登录后可以继续使用预测、回测和市场情绪工具，同时保留你的个人设置与分析偏好。'}
                </p>
                <div className="auth-side-points">
                  <div>
                    {isEnglish
                      ? 'Realtime quotes linked with market-wide data'
                      : '实时行情与全市场数据联动'}
                  </div>
                  <div>
                    {isEnglish
                      ? 'Visualized multi-model forecasts and backtests'
                      : '多模型预测与回测结果可视化'}
                  </div>
                  <div>
                    {isEnglish
                      ? 'Sentiment capture with keyword targeting'
                      : '支持按关键词定向抓取市场情绪'}
                  </div>
                </div>
              </Card.Body>
            </Card>
          </Col>

          <Col lg={6} className="d-flex">
            <Card className="auth-form-card w-100">
              <Card.Body>
                <PageLogo title="Login" subtitle="Account Access" glyph="L" tone="blue" compact />
                <h2 className="auth-form-title">{isEnglish ? 'Login to your account' : '登录账户'}</h2>
                <p className="auth-form-subtitle">
                  {isEnglish ? 'Sign in with your username or email' : '支持用户名或邮箱登录'}
                </p>

                {localError && <Alert variant="danger">{localError}</Alert>}

                <Form onSubmit={handleSubmit}>
                  <Form.Group className="mb-3">
                    <Form.Label>{isEnglish ? 'Username / Email' : '用户名 / 邮箱'}</Form.Label>
                    <Form.Control
                      type="text"
                      name="username"
                      value={formData.username}
                      onChange={handleChange}
                      placeholder={isEnglish ? 'Enter username or email' : '请输入用户名或邮箱'}
                      autoComplete="username"
                    />
                  </Form.Group>
                  <Form.Group className="mb-4">
                    <Form.Label>{isEnglish ? 'Password' : '密码'}</Form.Label>
                    <Form.Control
                      type="password"
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      placeholder={isEnglish ? 'Enter password' : '请输入密码'}
                      autoComplete="current-password"
                    />
                  </Form.Group>
                  <Button type="submit" className="w-100 auth-submit-btn" disabled={isLoading}>
                    {isLoading ? (
                      <>
                        <Spinner animation="border" size="sm" className="me-2" />
                        {isEnglish ? 'Signing in...' : '登录中...'}
                      </>
                    ) : (
                      isEnglish ? 'Login' : '登录'
                    )}
                  </Button>
                </Form>

                <div className="auth-footer">
                  {isEnglish ? "Don't have an account? " : '还没有账号？'}
                  <Link to="/register">{isEnglish ? 'Register now' : '立即注册'}</Link>
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </Container>
    </div>
  );
};

export default Login;
