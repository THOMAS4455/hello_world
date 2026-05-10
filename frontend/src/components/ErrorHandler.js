import React from 'react';
import { Alert, Button, Container } from 'react-bootstrap';
import { ArrowClockwise, House, BugFill } from 'react-bootstrap-icons';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null,
      errorId: null
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    const errorId = Date.now().toString(36);
    
    this.setState({
      error,
      errorInfo,
      errorId
    });

    // 记录错误到控制台
    console.error('错误边界捕获到错误:', {
      errorId,
      error,
      errorInfo,
      timestamp: new Date().toISOString()
    });

    // 可以在这里发送错误报告到监控服务
    this.reportError(error, errorInfo, errorId);
  }

  reportError = (error, errorInfo, errorId) => {
    // 这里可以集成错误监控服务，如 Sentry
    try {
      // 示例：发送错误报告
      const errorReport = {
        errorId,
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href
      };

      console.log('错误报告:', errorReport);
      
      // 可以发送到后端或监控服务
      // fetch('/api/errors/report', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(errorReport)
      // });
    } catch (reportError) {
      console.error('发送错误报告失败:', reportError);
    }
  };

  handleRetry = () => {
    this.setState({ 
      hasError: false, 
      error: null, 
      errorInfo: null,
      errorId: null 
    });
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      const isDevelopment = process.env.NODE_ENV === 'development';

      return (
        <Container className="py-5">
          <Alert variant="danger" className="text-center">
            <Alert.Heading className="d-flex align-items-center justify-content-center">
              <BugFill className="me-2" />
              应用程序遇到错误
            </Alert.Heading>
            
            <p className="mb-3">
              很抱歉，应用程序遇到了一个意外错误。我们已经记录了这个问题，正在努力修复。
            </p>

            <div className="d-flex justify-content-center gap-2 mb-4">
              <Button variant="outline-danger" onClick={this.handleRetry}>
                <ArrowClockwise className="me-2" />
                重试
              </Button>
              <Button variant="outline-primary" onClick={this.handleGoHome}>
                <House className="me-2" />
                返回首页
              </Button>
            </div>

            {isDevelopment && this.state.error && (
              <details className="text-start mt-4">
                <summary className="cursor-pointer">
                  <strong>错误详情 (开发模式)</strong>
                </summary>
                <div className="mt-3">
                  <div className="mb-3">
                    <strong>错误ID:</strong> {this.state.errorId}
                  </div>
                  <div className="mb-3">
                    <strong>错误消息:</strong>
                    <pre className="mt-1 p-2 bg-light rounded">
                      {this.state.error.toString()}
                    </pre>
                  </div>
                  <div className="mb-3">
                    <strong>错误堆栈:</strong>
                    <pre className="mt-1 p-2 bg-light rounded" style={{ fontSize: '0.875rem', maxHeight: '200px', overflow: 'auto' }}>
                      {this.state.error.stack}
                    </pre>
                  </div>
                  {this.state.errorInfo && (
                    <div className="mb-3">
                      <strong>组件堆栈:</strong>
                      <pre className="mt-1 p-2 bg-light rounded" style={{ fontSize: '0.875rem', maxHeight: '200px', overflow: 'auto' }}>
                        {this.state.errorInfo.componentStack}
                      </pre>
                    </div>
                  )}
                </div>
              </details>
            )}
          </Alert>
        </Container>
      );
    }

    return this.props.children;
  }
}

// 自定义错误处理Hook
export const useErrorHandler = () => {
  const [error, setError] = React.useState(null);
  const [isLoading, setIsLoading] = React.useState(false);

  const handleError = React.useCallback((error) => {
    console.error('自定义错误处理:', error);
    setError(error);
    
    // 可以在这里添加错误上报逻辑
    if (process.env.NODE_ENV === 'production') {
      // 发送错误到监控服务
      // reportError(error);
    }
  }, []);

  const clearError = React.useCallback(() => {
    setError(null);
  }, []);

  const executeWithErrorHandling = React.useCallback(async (asyncFunction) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await asyncFunction();
      setIsLoading(false);
      return result;
    } catch (error) {
      setIsLoading(false);
      handleError(error);
      throw error;
    }
  }, [handleError]);

  return {
    error,
    isLoading,
    handleError,
    clearError,
    executeWithErrorHandling
  };
};

// 网络错误处理组件
export const NetworkErrorHandler = ({ error, onRetry, onGoHome }) => {
  const getErrorMessage = (error) => {
    if (!error) return '未知错误';

    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      return '网络连接失败，请检查网络连接';
    }

    if (error.message.includes('500')) {
      return '服务器内部错误，请稍后重试';
    }

    if (error.message.includes('404')) {
      return '请求的资源不存在';
    }

    if (error.message.includes('401')) {
      return '未授权访问，请重新登录';
    }

    if (error.message.includes('403')) {
      return '访问被拒绝';
    }

    if (error.message.includes('timeout')) {
      return '请求超时，请检查网络连接';
    }

    return error.message || '发生未知错误';
  };

  const getErrorVariant = (error) => {
    if (!error) return 'warning';

    if (error.message.includes('500')) return 'danger';
    if (error.message.includes('404')) return 'warning';
    if (error.message.includes('401') || error.message.includes('403')) return 'danger';
    if (error.message.includes('timeout')) return 'warning';
    
    return 'warning';
  };

  return (
    <Alert variant={getErrorVariant(error)} className="text-center">
      <Alert.Heading>网络错误</Alert.Heading>
      <p className="mb-3">{getErrorMessage(error)}</p>
      
      <div className="d-flex justify-content-center gap-2">
        {onRetry && (
          <Button variant="outline-primary" onClick={onRetry}>
            <ArrowClockwise className="me-2" />
            重试
          </Button>
        )}
        {onGoHome && (
          <Button variant="outline-secondary" onClick={onGoHome}>
            <House className="me-2" />
            返回首页
          </Button>
        )}
      </div>
    </Alert>
  );
};

// 加载错误处理组件
export const LoadingErrorHandler = ({ isLoading, error, children, onRetry }) => {
  if (isLoading) {
    return (
      <div className="text-center p-4">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">加载中...</span>
        </div>
        <p className="mt-2">正在加载数据...</p>
      </div>
    );
  }

  if (error) {
    return <NetworkErrorHandler error={error} onRetry={onRetry} />;
  }

  return children;
};

// API错误处理工具
export const handleApiError = (error) => {
  console.error('API错误:', error);

  // 根据错误类型返回用户友好的错误消息
  if (error.response) {
    // 服务器响应错误
    const status = error.response.status;
    const message = error.response.data?.message || error.response.statusText;

    switch (status) {
      case 400:
        return '请求参数错误';
      case 401:
        return '未授权访问，请重新登录';
      case 403:
        return '访问被拒绝';
      case 404:
        return '请求的资源不存在';
      case 429:
        return '请求过于频繁，请稍后重试';
      case 500:
        return '服务器内部错误';
      case 502:
        return '网关错误';
      case 503:
        return '服务暂时不可用';
      default:
        return message || `服务器错误 (${status})`;
    }
  } else if (error.request) {
    // 网络错误
    return '网络连接失败，请检查网络连接';
  } else {
    // 其他错误
    return error.message || '发生未知错误';
  }
};

export default ErrorBoundary;
