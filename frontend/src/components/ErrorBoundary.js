import React from 'react';
import { Alert, Button, Container } from 'react-bootstrap';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error,
      errorInfo,
    });

    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.reportError(error, errorInfo);
  }

  reportError = (error, errorInfo) => {
    try {
      fetch('/api/errors/report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          error: error.toString(),
          stack: error.stack,
          componentStack: errorInfo?.componentStack || '',
          url: window.location.href,
          userAgent: navigator.userAgent,
          timestamp: new Date().toISOString(),
        }),
      }).catch((err) => {
        console.error('Failed to report error:', err);
      });
    } catch (err) {
      console.error('Error reporting failed:', err);
    }
  };

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <Container className="mt-5">
          <Alert variant="danger">
            <Alert.Heading>
              <i className="bi bi-exclamation-triangle me-2"></i>
              Application Error
            </Alert.Heading>

            <p className="mb-3">
              Sorry, the application encountered an unexpected error. We have recorded the issue and will work on a fix.
            </p>

            {process.env.NODE_ENV === 'development' && (
              <details className="mb-3">
                <summary>Error Details (development only)</summary>
                <pre className="mt-2 p-3 bg-light rounded">
                  <code>
                    {this.state.error && this.state.error.toString()}
                    <br />
                    <br />
                    {this.state.errorInfo?.componentStack || '(no component stack)'}
                  </code>
                </pre>
              </details>
            )}

            <div className="d-flex gap-2">
              <Button variant="primary" onClick={this.handleReload}>
                <i className="bi bi-arrow-clockwise me-2"></i>
                Reload
              </Button>
              <Button variant="outline-primary" onClick={this.handleGoHome}>
                <i className="bi bi-house me-2"></i>
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

export default ErrorBoundary;
