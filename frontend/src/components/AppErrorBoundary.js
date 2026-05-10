import React from 'react';
import { Alert, Button, Container } from 'react-bootstrap';
import { House, ArrowClockwise } from 'react-bootstrap-icons';

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error,
      errorInfo,
    });

    console.error('Application error:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <Container className="py-5">
          <Alert variant="danger">
            <Alert.Heading className="d-flex align-items-center">Application Error</Alert.Heading>

            <p className="mb-3">
              Sorry, the application hit an unexpected error. The issue has been logged.
            </p>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mb-3">
                <summary>Error details (development mode)</summary>
                <pre className="mt-2 p-2 bg-light rounded" style={{ fontSize: '0.875rem' }}>
                  {this.state.error.toString()}
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}

            <div className="d-flex gap-2">
              <Button variant="outline-danger" onClick={this.handleRetry}>
                <ArrowClockwise className="me-2" />
                Retry
              </Button>
              <Button variant="outline-primary" onClick={this.handleGoHome}>
                <House className="me-2" />
                Go Home
              </Button>
            </div>
          </Alert>
        </Container>
      );
    }

    return this.props.children;
  }
}

export default AppErrorBoundary;
