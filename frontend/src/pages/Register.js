import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Alert, Button, Card, Col, Container, Form, Row, Spinner } from 'react-bootstrap';
import { useAppI18n } from '../i18n';
import PageLogo from '../components/PageLogo';
import { useRegisterMutation } from '../services/apiService';
import '../styles/AuthPages.css';

const Register = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const navigate = useNavigate();
  const [registerUser, { isLoading }] = useRegisterMutation();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const username = formData.username.trim();
    const email = formData.email.trim();
    const password = formData.password;
    const confirmPassword = formData.confirmPassword;

    if (!username || !email || !password || !confirmPassword) {
      setError(isEnglish ? 'Please complete the registration form.' : '请完整填写注册信息');
      return;
    }
    if (password.length < 6) {
      setError(isEnglish ? 'Password must be at least 6 characters.' : '密码至少 6 位');
      return;
    }
    if (password !== confirmPassword) {
      setError(isEnglish ? 'The passwords do not match.' : '两次输入的密码不一致');
      return;
    }

    try {
      const response = await registerUser({ username, email, password }).unwrap();
      if (!response?.success) {
        throw new Error(response?.message || (isEnglish ? 'Registration failed' : '注册失败'));
      }
      setSuccess(
        isEnglish ? 'Registration successful. Redirecting to the login page...' : '注册成功，正在跳转到登录页'
      );
      setTimeout(() => navigate('/login'), 1200);
    } catch (err) {
      setError(
        err?.data?.message ||
          err?.message ||
          (isEnglish ? 'Registration failed. Please try again later.' : '注册失败，请稍后重试')
      );
    }
  };

  return (
    <div className="auth-page auth-register-page">
      <Container fluid="xl" className="auth-container">
        <Row className="g-4 align-items-stretch">
          <Col lg={6} className="d-flex">
            <Card className="auth-side-card w-100">
              <Card.Body>
                <PageLogo title="AlphaScope" subtitle="Create Account" glyph="R" tone="teal" compact />
                <div className="auth-side-tag">{isEnglish ? 'New User Registration' : '新用户注册'}</div>
                <h1 className="auth-side-title">{isEnglish ? 'Create your account' : '创建你的账号'}</h1>
                <p className="auth-side-text">
                  {isEnglish
                    ? 'After registering, you can save preferences, manage analysis results, and share one account state across pages.'
                    : '注册后可以保存个人偏好、管理分析结果，并在不同页面共享同一账户状态。'}
                </p>
                <div className="auth-side-points">
                  <div>{isEnglish ? 'One account across forecasts, backtests, and sentiment' : '一个账号贯通预测、回测与情绪分析'}</div>
                  <div>{isEnglish ? 'Profile and settings can be stored long-term' : '个人资料与设置可长期保存'}</div>
                  <div>{isEnglish ? 'Ready for future permissions and team collaboration' : '后续可扩展权限体系与团队协作'}</div>
                </div>
              </Card.Body>
            </Card>
          </Col>

          <Col lg={6} className="d-flex">
            <Card className="auth-form-card w-100">
              <Card.Body>
                <PageLogo title="Register" subtitle="Join Platform" glyph="R" tone="rose" compact />
                <h2 className="auth-form-title">{isEnglish ? 'Create account' : '注册账号'}</h2>
                <p className="auth-form-subtitle">
                  {isEnglish ? 'Fill in the form to start using the system right away' : '填写信息后即可立即使用系统'}
                </p>

                {error && <Alert variant="danger">{error}</Alert>}
                {success && <Alert variant="success">{success}</Alert>}

                <Form onSubmit={handleSubmit}>
                  <Form.Group className="mb-3">
                    <Form.Label>{isEnglish ? 'Username' : '用户名'}</Form.Label>
                    <Form.Control
                      type="text"
                      name="username"
                      value={formData.username}
                      onChange={handleChange}
                      placeholder={isEnglish ? 'At least 3 characters' : '至少 3 个字符'}
                    />
                  </Form.Group>
                  <Form.Group className="mb-3">
                    <Form.Label>{isEnglish ? 'Email' : '邮箱'}</Form.Label>
                    <Form.Control
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      placeholder={isEnglish ? 'Enter your email address' : '请输入邮箱地址'}
                    />
                  </Form.Group>
                  <Form.Group className="mb-3">
                    <Form.Label>{isEnglish ? 'Password' : '密码'}</Form.Label>
                    <Form.Control
                      type="password"
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      placeholder={isEnglish ? 'At least 6 characters' : '至少 6 位'}
                      autoComplete="new-password"
                    />
                  </Form.Group>
                  <Form.Group className="mb-4">
                    <Form.Label>{isEnglish ? 'Confirm Password' : '确认密码'}</Form.Label>
                    <Form.Control
                      type="password"
                      name="confirmPassword"
                      value={formData.confirmPassword}
                      onChange={handleChange}
                      placeholder={isEnglish ? 'Enter the password again' : '再次输入密码'}
                      autoComplete="new-password"
                    />
                  </Form.Group>

                  <Button type="submit" className="w-100 auth-submit-btn" disabled={isLoading}>
                    {isLoading ? (
                      <>
                        <Spinner animation="border" size="sm" className="me-2" />
                        {isEnglish ? 'Registering...' : '注册中...'}
                      </>
                    ) : (
                      isEnglish ? 'Register' : '注册'
                    )}
                  </Button>
                </Form>

                <div className="auth-footer">
                  {isEnglish ? 'Already have an account? ' : '已有账号？'}
                  <Link to="/login">{isEnglish ? 'Go to login' : '去登录'}</Link>
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </Container>
    </div>
  );
};

export default Register;
