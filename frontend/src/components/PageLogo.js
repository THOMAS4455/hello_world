import React from 'react';
import '../styles/PageLogo.css';

const toneClassMap = {
  orange: 'logo-tone-orange',
  teal: 'logo-tone-teal',
  blue: 'logo-tone-blue',
  rose: 'logo-tone-rose',
};

const PageLogo = ({
  title = 'AlphaScope',
  subtitle = '',
  compact = false,
  glyph = 'A',
  tone = 'orange',
}) => {
  const toneClass = toneClassMap[tone] || toneClassMap.orange;

  return (
    <div className={`page-logo ${compact ? 'page-logo-compact' : ''}`}>
      <div className={`page-logo-mark ${toneClass}`}>{String(glyph).slice(0, 1)}</div>
      <div className="page-logo-text">
        <div className="page-logo-title">{title}</div>
        {subtitle ? <div className="page-logo-subtitle">{subtitle}</div> : null}
      </div>
    </div>
  );
};

export default PageLogo;
