import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Badge, Button, Container, Nav, Navbar } from 'react-bootstrap';
import { useDispatch, useSelector } from 'react-redux';
import { useAppI18n } from '../i18n';
import PageLogo from './PageLogo';
import { logout } from '../store/slices/authSlice';
import '../styles/Navigation.css';

const Navigation = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const isAuthenticated = useSelector((state) => Boolean(state?.auth?.isAuthenticated));
  const username = useSelector((state) => state?.auth?.user?.username || '');
  const roles = useSelector((state) => state?.auth?.roles || []);
  const isAdmin = Array.isArray(roles) && roles.some((r) => String(r).toLowerCase() === 'admin');
  const { t } = useAppI18n();

  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  return (
    <Navbar expand="lg" fixed="top" className="main-navbar">
      <Container fluid="xl">
        <Navbar.Brand as={NavLink} to="/" className="brand-text">
          <PageLogo title={t('appTitle')} glyph="A" tone="orange" compact />
          <Badge bg="light" text="dark" className="ms-2">
            BETA
          </Badge>
        </Navbar.Brand>
        <Navbar.Toggle aria-controls="main-navbar-nav" />
        <Navbar.Collapse id="main-navbar-nav">
          <Nav className="me-auto">
            <Nav.Link as={NavLink} to="/" end>
              {t('navHome')}
            </Nav.Link>
            <Nav.Link as={NavLink} to="/dashboard">
              {t('navDashboard')}
            </Nav.Link>
            <Nav.Link as={NavLink} to="/predictions">
              {t('navPredictions')}
            </Nav.Link>
            <Nav.Link as={NavLink} to="/backtest">
              {t('navBacktest')}
            </Nav.Link>
            <Nav.Link as={NavLink} to="/market-sentiment">
              {t('navSentiment')}
            </Nav.Link>
            <Nav.Link as={NavLink} to="/ai-chat">
              {t('navAiChat')}
            </Nav.Link>
          </Nav>

          <Nav className="align-items-lg-center gap-2">
            {!isAuthenticated ? (
              <>
                <Nav.Link as={NavLink} to="/login">
                  {t('navLogin')}
                </Nav.Link>
                <Nav.Link as={NavLink} to="/register">
                  {t('navRegister')}
                </Nav.Link>
              </>
            ) : (
              <>
                {isAdmin && (
                  <Nav.Link as={NavLink} to="/admin">
                    {t('navAdmin')}
                  </Nav.Link>
                )}
                <Nav.Link as={NavLink} to="/profile">
                  {username ? `${t('navUserPrefix')}: ${username}` : t('navProfile')}
                </Nav.Link>
                <Button variant="outline-light" size="sm" onClick={handleLogout}>
                  {t('navLogout')}
                </Button>
              </>
            )}
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default Navigation;
