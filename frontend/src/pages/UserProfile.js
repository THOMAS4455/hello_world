import React, { useState } from 'react';
import { Container, Row, Col, Card, Form, Button, Alert } from 'react-bootstrap';
import { useAppI18n } from '../i18n';

const UserProfile = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const [profile, setProfile] = useState({
    username: 'demo_user',
    email: 'demo@example.com',
    phone: '',
    company: '',
    bio: '',
  });
  const [saved, setSaved] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setProfile((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    localStorage.setItem('userProfile', JSON.stringify(profile));
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <Container fluid className="py-4">
      <Row>
        <Col md={8} className="mx-auto">
          <Card>
            <Card.Header as="h4">{isEnglish ? 'User Profile' : '用户资料'}</Card.Header>
            <Card.Body>
              {saved && (
                <Alert variant="success" className="mb-3">
                  {isEnglish ? 'Profile updated successfully.' : '资料更新成功！'}
                </Alert>
              )}

              <Row className="mb-4">
                <Col md={4} className="text-center">
                  <div className="avatar-placeholder mb-3">
                    <div
                      style={{
                        width: '120px',
                        height: '120px',
                        borderRadius: '50%',
                        backgroundColor: '#007bff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        margin: '0 auto',
                        color: 'white',
                        fontSize: '48px',
                        fontWeight: 'bold',
                      }}
                    >
                      {profile.username.charAt(0).toUpperCase()}
                    </div>
                  </div>
                  <Button variant="outline-primary" size="sm">
                    {isEnglish ? 'Change Avatar' : '更换头像'}
                  </Button>
                </Col>

                <Col md={8}>
                  <Form onSubmit={handleSubmit}>
                    <Form.Group className="mb-3">
                      <Form.Label>{isEnglish ? 'Username' : '用户名'}</Form.Label>
                      <Form.Control type="text" name="username" value={profile.username} onChange={handleChange} required />
                    </Form.Group>

                    <Form.Group className="mb-3">
                      <Form.Label>{isEnglish ? 'Email' : '邮箱'}</Form.Label>
                      <Form.Control type="email" name="email" value={profile.email} onChange={handleChange} required />
                    </Form.Group>

                    <Form.Group className="mb-3">
                      <Form.Label>{isEnglish ? 'Phone' : '电话'}</Form.Label>
                      <Form.Control type="tel" name="phone" value={profile.phone} onChange={handleChange} />
                    </Form.Group>

                    <Form.Group className="mb-3">
                      <Form.Label>{isEnglish ? 'Company' : '公司'}</Form.Label>
                      <Form.Control type="text" name="company" value={profile.company} onChange={handleChange} />
                    </Form.Group>

                    <Form.Group className="mb-3">
                      <Form.Label>{isEnglish ? 'Bio' : '个人简介'}</Form.Label>
                      <Form.Control as="textarea" name="bio" value={profile.bio} onChange={handleChange} rows={3} />
                    </Form.Group>

                    <Button variant="primary" type="submit">
                      {isEnglish ? 'Save Profile' : '保存资料'}
                    </Button>
                  </Form>
                </Col>
              </Row>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default UserProfile;
