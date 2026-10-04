import React from 'react';
import { Nav } from 'react-bootstrap';
import { NavLink, useLocation } from 'react-router-dom';
import { useAppI18n } from '../../i18n';

const TABS = [
  { segment: 'workbench', keyEn: 'Workbench', keyZh: '工作台' },
  { segment: 'portfolio', keyEn: 'Portfolio', keyZh: '组合' },
  { segment: 'forecast', keyEn: 'Forecast', keyZh: '预测' },
  { segment: 'backtest', keyEn: 'Backtest', keyZh: '回测' },
  { segment: 'paper', keyEn: 'Paper Twin', keyZh: '模拟盘' },
  { segment: 'screener', keyEn: 'Daily Picks', keyZh: '每日选股' },
  { segment: 'insights', keyEn: 'Insights', keyZh: '洞察' },
];

const InvestmentSubNav = () => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const location = useLocation();
  const search = location.search;

  return (
    <Nav variant="tabs" className="investment-tabs mb-3 flex-wrap">
      {TABS.map((tab) => (
        <Nav.Item key={tab.segment}>
          <Nav.Link
            as={NavLink}
            to={{ pathname: `/investment/${tab.segment}`, search }}
            className={({ isActive }) => (isActive ? 'active' : undefined)}
          >
            {isEnglish ? tab.keyEn : tab.keyZh}
          </Nav.Link>
        </Nav.Item>
      ))}
    </Nav>
  );
};

export default InvestmentSubNav;
