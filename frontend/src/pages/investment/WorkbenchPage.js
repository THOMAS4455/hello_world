import React, { useMemo, useState } from 'react';
import { Alert, Badge, Button, Card, Col, Form, Row, Spinner, Table } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { useResearchWorkspace } from '../../contexts/ResearchWorkspaceContext';
import stockApiService from '../../services/stockApi';
import './WorkbenchPage.css';

const emptyHolding = { symbol: '', quantity: 100, available_quantity: 100, average_cost: '' };
const pct = (value) => (Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(1)}%` : '-');

export default function WorkbenchPage() {
  const navigate = useNavigate();
  const { watchlist, isEnglish, setError, clearError } = useResearchWorkspace();
  const [candidates, setCandidates] = useState(null);
  const [advice, setAdvice] = useState(null);
  const [review, setReview] = useState(null);
  const [holding, setHolding] = useState(emptyHolding);
  const [loading, setLoading] = useState('');
  const labels = useMemo(() => isEnglish ? {
    title: 'A-share research workbench', scan: 'Screen watchlist', holding: 'Holding diagnosis', review: 'Multi-agent review',
  } : { title: 'A 股研究工作台', scan: '扫描自选池', holding: '持仓诊断', review: '多智能体研判' }, [isEnglish]);

  const execute = async (kind, action) => {
    setLoading(kind); clearError();
    try { await action(); } catch (error) { setError(error.message || 'Request failed'); } finally { setLoading(''); }
  };
  const scan = () => execute('scan', async () => setCandidates(await stockApiService.getCandidateResearch(watchlist)));
  const diagnose = () => execute('holding', async () => setAdvice(await stockApiService.getHoldingAdvice([{
    ...holding, quantity: Number(holding.quantity), available_quantity: Number(holding.available_quantity), average_cost: Number(holding.average_cost),
  }])));
  const runReview = (symbol) => execute('review', async () => setReview(await stockApiService.getTradingAgentsReview(symbol)));

  return <div className="workbench-page">
    <section className="workbench-head"><div><p className="workbench-kicker">V0.1 / END-OF-DAY RESEARCH</p><h2>{labels.title}</h2><p>从候选筛选、仓位风险到多角色研判，所有结论均保留条件和失效线。</p></div><div className="workbench-status"><span>数据模式</span><strong>研究 / 非实盘</strong></div></section>
    <Row className="g-3 mb-3"><Col lg={7}><Card className="workbench-panel h-100"><Card.Header><span>{labels.scan}</span><Button size="sm" onClick={scan} disabled={!watchlist.length || loading === 'scan'}>{loading === 'scan' ? <Spinner size="sm" /> : labels.scan}</Button></Card.Header><Card.Body>{!watchlist.length ? <Alert variant="light" className="mb-0">请先在组合页添加自选股票。</Alert> : !candidates ? <p className="text-muted mb-0">当前自选 {watchlist.length} 只。扫描将计算动量、均线趋势、流动性与 ATR 风险。</p> : <><div className="workbench-coverage">已加载 {candidates.coverage?.loaded || 0} / {candidates.coverage?.requested || 0} 只股票 <Badge bg="secondary">{candidates.market_regime}</Badge></div><Table responsive hover size="sm" className="workbench-table"><thead><tr><th>代码</th><th>评分</th><th>条件入场</th><th>止损</th><th /></tr></thead><tbody>{(candidates.candidates || []).map(row => <tr key={row.symbol}><td><strong>{row.symbol}</strong><small>{row.direction || 'factor'}</small></td><td>{row.score}</td><td>{row.entry_low}-{row.entry_high}</td><td className="workbench-risk">{row.stop_price}</td><td><Button variant="link" size="sm" onClick={() => runReview(row.symbol)}>研判</Button></td></tr>)}</tbody></Table>{!(candidates.candidates || []).length && <p className="text-muted mb-0">没有候选通过当前阈值。</p>}</>}</Card.Body></Card></Col>
    <Col lg={5}><Card className="workbench-panel h-100"><Card.Header>{labels.holding}</Card.Header><Card.Body><Form onSubmit={(e) => { e.preventDefault(); diagnose(); }}><Row className="g-2"><Col sm={6}><Form.Label>股票代码</Form.Label><Form.Control required value={holding.symbol} onChange={e => setHolding({...holding, symbol:e.target.value})} placeholder="600519" /></Col><Col sm={6}><Form.Label>持仓成本</Form.Label><Form.Control required type="number" step="0.01" value={holding.average_cost} onChange={e => setHolding({...holding, average_cost:e.target.value})} /></Col><Col sm={6}><Form.Label>持仓数量</Form.Label><Form.Control type="number" value={holding.quantity} onChange={e => setHolding({...holding, quantity:e.target.value})} /></Col><Col sm={6}><Form.Label>可卖数量</Form.Label><Form.Control type="number" value={holding.available_quantity} onChange={e => setHolding({...holding, available_quantity:e.target.value})} /></Col></Row><Button className="mt-3" type="submit" disabled={loading === 'holding'}>{loading === 'holding' ? <Spinner size="sm" /> : labels.holding}</Button></Form>{advice?.items?.[0] && <div className="workbench-advice"><Badge bg={advice.items[0].action === 'hold' ? 'success' : 'warning'}>{advice.items[0].action}</Badge><strong>{advice.items[0].symbol} {pct(advice.items[0].profit_loss_pct)}</strong><span>MA20 {advice.items[0].ma20} / RSI {advice.items[0].rsi14}</span><span>风险线 {advice.items[0].stop_price}，移动止损 {advice.items[0].trailing_stop_price}</span><small>{advice.items[0].reasons?.join(' · ')}</small></div>}</Card.Body></Card></Col></Row>
    <Card className="workbench-panel"><Card.Header>{labels.review}</Card.Header><Card.Body>{!review ? <p className="text-muted mb-0">从候选列表点击“研判”生成多头、空头、风控与交易角色的综合研究意见。</p> : <><div className="workbench-agent-meta"><Badge bg="dark">{review.framework}</Badge>{review.source_available ? <span>TradingAgents 源码已发现</span> : <span>兼容模式</span>}</div><div className="workbench-report">{review.analysis}</div></>}</Card.Body></Card>
  </div>;
}
