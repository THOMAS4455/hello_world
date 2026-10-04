import React from 'react';
import { Badge, Card, ProgressBar } from 'react-bootstrap';
import { useAppI18n } from '../i18n';
import '../styles/DecisionCard.css';

const clampPercent = (value) => Math.max(0, Math.min(100, Number(value || 0)));

const DecisionCard = ({
  title,
  summary = '',
  direction = 'neutral',
  confidence = 0,
  quality = 'medium',
  riskNote = '',
  evidence = [],
}) => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';

  const toneMap = {
    bullish: { className: 'bg-market-up', text: isEnglish ? 'Bullish' : '偏多' },
    bearish: { className: 'bg-market-down', text: isEnglish ? 'Bearish' : '偏空' },
    neutral: { className: 'bg-secondary', text: isEnglish ? 'Neutral' : '中性' },
  };

  const qualityMap = {
    high: { badge: 'success', text: isEnglish ? 'High Confidence' : '高可信' },
    medium: { badge: 'warning', text: isEnglish ? 'Medium Confidence' : '中可信' },
    low: { badge: 'danger', text: isEnglish ? 'Low Confidence' : '低可信' },
  };

  const tone = toneMap[direction] || toneMap.neutral;
  const qualityInfo = qualityMap[quality] || qualityMap.medium;
  const confidencePct = clampPercent(confidence * 100);

  return (
    <Card className="decision-card mb-3">
      <Card.Header className="d-flex justify-content-between align-items-center">
        <span>{title || (isEnglish ? 'Unified Decision Summary' : '统一决策结论')}</span>
        <div className="d-flex gap-2">
          <Badge className={tone.className}>{tone.text}</Badge>
          <Badge bg={qualityInfo.badge}>{qualityInfo.text}</Badge>
        </div>
      </Card.Header>
      <Card.Body>
        <div className="decision-summary">{summary || (isEnglish ? 'No conclusion yet' : '暂无结论')}</div>
        <div className="decision-confidence mt-3">
          <div className="d-flex justify-content-between">
            <span>{isEnglish ? 'Decision confidence' : '决策置信度'}</span>
            <strong>{confidencePct.toFixed(1)}%</strong>
          </div>
          <ProgressBar now={confidencePct} />
        </div>

        {Array.isArray(evidence) && evidence.length > 0 && (
          <div className="decision-evidence mt-3">
            {evidence.map((item) => (
              <div className="decision-evidence-item" key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        )}

        {riskNote && (
          <div className="decision-risk mt-3">
            {isEnglish ? 'Risk note: ' : '风险提示：'}
            {riskNote}
          </div>
        )}
      </Card.Body>
    </Card>
  );
};

export default DecisionCard;
