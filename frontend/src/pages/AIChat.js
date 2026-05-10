import React, { useEffect, useState } from 'react';
import { Alert, Card, Container } from 'react-bootstrap';
import { useAppI18n } from '../i18n';
import AIChatInterface from '../components/AIChatInterface';
import { handleApiError } from '../components/ErrorHandler';
import PageLogo from '../components/PageLogo';
import '../styles/AIChat.css';

const AIChat = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setMessages([
      {
        id: Date.now(),
        content: isEnglish
          ? 'Hello, I am your AI investment assistant. You can ask me about stock trends, risk, strategy backtests, and position suggestions.'
          : '你好，我是你的 AI 投资助手。你可以直接问我股票趋势、风险、策略回测和仓位建议。',
        type: 'ai',
        timestamp: new Date(),
        metadata: { confidence: 100, sentiment: 'neutral' },
      },
    ]);
  }, [isEnglish]);

  const handleSendMessage = async (messageText) => {
    const userMessage = {
      id: Date.now(),
      content: messageText,
      type: 'user',
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageText }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const data = await response.json();
      const payload = data?.data || {};
      const aiMessage = {
        id: Date.now() + 1,
        content:
          payload.response ||
          (isEnglish
            ? 'Sorry, I cannot answer that right now. Please try again later.'
            : '抱歉，我暂时无法回答这个问题，请稍后重试。'),
        type: 'ai',
        timestamp: new Date(),
        metadata: {
          confidence: payload.confidence || 75,
          sentiment: payload.sentiment || 'neutral',
        },
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          content: `${isEnglish ? 'Send failed: ' : '发送失败：'}${handleApiError(e)}`,
          type: 'system',
          timestamp: new Date(),
        },
      ]);
      setError(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container className="ai-chat-page py-3 py-md-4">
      <Card className="ai-chat-shell">
        <Card.Header className="ai-chat-header">
          <PageLogo title="AI Assistant" subtitle="Conversational Research" glyph="Q" tone="teal" />
          <div className="ai-chat-title mt-2">{isEnglish ? 'AI Investment Assistant' : 'AI 投资助手'}</div>
          <div className="ai-chat-subtitle">
            {isEnglish ? 'Supports stock analysis, strategy suggestions, and risk judgment' : '支持股票分析、策略建议、风险判断'}
          </div>
        </Card.Header>
        <Card.Body className="p-0">
          {error && (
            <Alert variant="danger" className="m-3 mb-0">
              {isEnglish ? 'AI service connection error. Please try again later.' : 'AI 服务连接异常，请稍后重试。'}
            </Alert>
          )}
          <AIChatInterface messages={messages} loading={loading} onSendMessage={handleSendMessage} />
        </Card.Body>
      </Card>
    </Container>
  );
};

export default AIChat;
