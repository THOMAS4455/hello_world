import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Form, Row, Spinner } from 'react-bootstrap';
import { useDispatch } from 'react-redux';
import { useAppI18n } from '../i18n';
import stockApiService from '../services/stockApi';
import { updateUser } from '../store/slices/authSlice';

const emptyProfile = {
  username: '',
  email: '',
  phone: '',
  company: '',
  bio: '',
};

const UserProfile = () => {
  const dispatch = useDispatch();
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const [profile, setProfile] = useState(emptyProfile);
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
          username: user?.username || '',
          email: user?.email || '',
          phone: user?.profile?.phone || '',
          company: user?.profile?.company || '',
          bio: user?.profile?.bio || '',
        };
        setProfile(merged);
        dispatch(updateUser(user || {}));
      } catch (err) {
        setError(err?.message || (isEnglish ? 'Failed to load profile.' : '加载资料失败。'));
      } finally {
        setLoading(false);
      }
    };

    loadProfile();
  }, [dispatch, isEnglish]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setProfile((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    setError('');
    try {
      const user = await stockApiService.updateUserProfile({
        phone: profile.phone,
        company: profile.company,
        bio: profile.bio,
      });
      setProfile((prev) => ({
        ...prev,
        username: user?.username || prev.username,
        email: user?.email || prev.email,
        phone: user?.profile?.phone || '',
        company: user?.profile?.company || '',
        bio: user?.profile?.bio || '',
      }));
      dispatch(updateUser(user || {}));
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err?.message || (isEnglish ? 'Failed to update profile.' : '更新资料失败。'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="analysis-page profile-page">
      <div className="ds-page-narrow">
        <Card>
            <Card.Header as="h4">{isEnglish ? 'User Profile' : '用户资料'}</Card.Header>
            <Card.Body>
              {loading ? (
                <div className="text-center py-4">
                  <Spinner animation="border" />
                </div>
              ) : (
                <>
                  {saved && (
                    <Alert variant="success" className="mb-3">
                      {isEnglish ? 'Profile updated successfully.' : '资料已更新。'}
                    </Alert>
                  )}
                  {error && (
                    <Alert variant="danger" className="mb-3">
                      {error}
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
                          {(profile.username || '?').charAt(0).toUpperCase()}
                        </div>
                      </div>
                    </Col>

                    <Col md={8}>
                      <Form onSubmit={handleSubmit}>
                        <Form.Group className="mb-3">
                          <Form.Label>{isEnglish ? 'Username' : '用户名'}</Form.Label>
                          <Form.Control type="text" name="username" value={profile.username} disabled />
                        </Form.Group>

                        <Form.Group className="mb-3">
                          <Form.Label>{isEnglish ? 'Email' : '邮箱'}</Form.Label>
                          <Form.Control type="email" name="email" value={profile.email} disabled />
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

                        <Button variant="primary" type="submit" disabled={saving}>
                          {saving ? (isEnglish ? 'Saving...' : '保存中...') : isEnglish ? 'Save Profile' : '保存资料'}
                        </Button>
                      </Form>
                    </Col>
                  </Row>
                </>
              )}
            </Card.Body>
        </Card>
      </div>
    </div>
  );
};

export default UserProfile;
