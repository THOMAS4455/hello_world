import React from 'react';
import { Form, ButtonGroup, Button } from 'react-bootstrap';
import { useAppI18n } from '../i18n';

const AIModeSelector = ({ mode, onModeChange, disabled = false }) => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';

  const modes = isEnglish
    ? [
        { value: 'normal', label: 'Normal Chat', description: 'Friendly conversational mode' },
        { value: 'financial', label: 'Professional Analysis', description: 'Professional financial analysis' },
        { value: 'hybrid', label: 'Hybrid Mode', description: 'Conversation + professional analysis' },
      ]
    : [
        { value: 'normal', label: '普通对话', description: '友好的对话模式' },
        { value: 'financial', label: '专业分析', description: '专业金融分析' },
        { value: 'hybrid', label: '混合模式', description: '对话 + 专业分析' },
      ];

  return (
    <div className="ai-mode-selector mb-3">
      <Form.Label className="fw-bold">{isEnglish ? 'AI Assistant Mode' : 'AI助手模式'}</Form.Label>
      <ButtonGroup className="w-100" role="group">
        {modes.map((modeOption) => (
          <Button
            key={modeOption.value}
            variant={mode === modeOption.value ? 'primary' : 'outline-primary'}
            onClick={() => onModeChange(modeOption.value)}
            disabled={disabled}
            className="flex-fill"
            title={modeOption.description}
          >
            <div className="d-flex flex-column">
              <span>{modeOption.label}</span>
              <small className="text-muted">{modeOption.description}</small>
            </div>
          </Button>
        ))}
      </ButtonGroup>
    </div>
  );
};

export default AIModeSelector;
