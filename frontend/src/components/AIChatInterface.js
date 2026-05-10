import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Badge, Button, Form, Spinner } from 'react-bootstrap';
import { Cpu, ExclamationTriangle, Person, Send } from 'react-bootstrap-icons';
import { useAppI18n } from '../i18n';

const AIChatInterface = ({ onSendMessage, loading, messages }) => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const [inputMessage, setInputMessage] = useState('');
  const messagesEndRef = useRef(null);

  const suggestions = isEnglish
    ? [
        'Analyze Kweichow Moutai short-term momentum',
        "How is today's overall market sentiment?",
        'Give me three tech stocks worth watching',
        'Is Ping An Bank suitable for a medium-term hold?',
      ]
    : [
        '分析一下贵州茅台的短期趋势',
        '今天大盘情绪如何',
        '给我三只可关注的科技股',
        '平安银行适合中线持有吗',
      ];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = inputMessage.trim();
    if (!trimmed || loading) return;
    await onSendMessage(trimmed);
    setInputMessage('');
  };

  const renderMessageIcon = (type) => {
    if (type === 'user') return <Person size={15} />;
    if (type === 'system') return <ExclamationTriangle size={15} />;
    return <Cpu size={15} />;
  };

  const messageLabel = useMemo(
    () => ({
      user: isEnglish ? 'You' : '你',
      ai: isEnglish ? 'AI Assistant' : 'AI 助手',
      system: isEnglish ? 'System' : '系统',
    }),
    [isEnglish]
  );

  return (
    <div className="ai-chat-interface">
      <div className="ai-chat-messages">
        {messages.length === 0 ? (
          <div className="ai-chat-empty">
            <Cpu size={40} />
            <h5 className="mb-2 mt-2">{isEnglish ? 'Start a conversation' : '开始对话'}</h5>
            <p className="mb-3">
              {isEnglish
                ? 'Ask about price trends, position sizing, risk controls, or backtest ideas.'
                : '你可以咨询个股趋势、仓位建议、风险控制和回测思路。'}
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`chat-row ${message.type === 'user' ? 'is-user' : 'is-assistant'}`}
            >
              <div className={`chat-bubble ${message.type}`}>
                <div className="chat-meta">
                  <span className="chat-author">
                    {renderMessageIcon(message.type)}
                    <span>{messageLabel[message.type] || messageLabel.ai}</span>
                  </span>
                  <span className="chat-time">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </span>
                </div>

                <div className="chat-content">{message.content}</div>

                {message.type === 'ai' && message.metadata && (
                  <div className="chat-extra">
                    <Badge bg="light" text="dark">
                      {isEnglish ? 'Confidence ' : '置信度 '}
                      {message.metadata.confidence || 0}%
                    </Badge>
                    <Badge bg="light" text="dark">
                      {isEnglish ? 'Sentiment ' : '情绪 '}
                      {message.metadata.sentiment || 'neutral'}
                    </Badge>
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="chat-row is-assistant">
            <div className="chat-bubble ai">
              <div className="chat-meta">
                <span className="chat-author">
                  <Cpu size={15} />
                  <span>{messageLabel.ai}</span>
                </span>
              </div>
              <div className="chat-thinking">
                <Spinner animation="border" size="sm" />
                <span>{isEnglish ? 'Analyzing...' : '正在分析中...'}</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="ai-chat-suggestions">
        {suggestions.map((item) => (
          <button
            key={item}
            className="suggestion-pill"
            type="button"
            onClick={() => setInputMessage(item)}
            disabled={loading}
          >
            {item}
          </button>
        ))}
      </div>

      <div className="ai-chat-input">
        <Form onSubmit={handleSubmit}>
          <div className="ai-chat-input-row">
            <Form.Control
              type="text"
              placeholder={
                isEnglish
                  ? 'Enter your question, for example: How does the new energy sector look next week?'
                  : '输入你的问题，例如：新能源板块下周怎么看？'
              }
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              disabled={loading}
            />
            <Button type="submit" variant="primary" disabled={loading || !inputMessage.trim()}>
              {loading ? <Spinner animation="border" size="sm" /> : <Send size={16} />}
            </Button>
          </div>
        </Form>
      </div>
    </div>
  );
};

export default AIChatInterface;
