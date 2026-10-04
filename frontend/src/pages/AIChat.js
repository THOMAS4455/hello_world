import React, { useEffect, useState } from 'react';
import { Alert, Card } from 'react-bootstrap';
import { useAppI18n } from '../i18n';
import AIChatInterface from '../components/AIChatInterface';
import { handleApiError } from '../components/ErrorHandler';
import PageLogo from '../components/PageLogo';
import stockApiService from '../services/stockApi';
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
          ? 'Hello, I am your AI investment assistant. Ask me about stock trends, risk, strategy backtests, and position sizing.'
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
      const payload = await stockApiService.sendAIMessage(messageText);
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
    <div className="analysis-page ai-chat-page">
      <Card className="ai-chat-shell">
        <Card.Header className="ai-chat-header">
          <PageLogo
            title={isEnglish ? 'AI Assistant' : 'AI 助手'}
            subtitle={isEnglish ? 'Conversational research workspace' : '对话式研究工作台'}
            glyph="Q"
            tone="blue"
          />
          <div className="ai-chat-title mt-2">{isEnglish ? 'AI Investment Assistant' : 'AI 投资助手'}</div>
          <div className="ai-chat-subtitle">
            {isEnglish ? 'Supports stock analysis, strategy suggestions, and risk judgment' : '支持股票分析、策略建议和风险判断'}
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
    </div>
  );
};

export default AIChat;
