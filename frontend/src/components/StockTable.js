import React, { useState } from 'react';
import { Table, Badge, Button, Form, InputGroup, Pagination } from 'react-bootstrap';
import { Search, ArrowUp, ArrowDown, GraphUp, GraphDown, Eye, Cpu } from 'react-bootstrap-icons';
import { useAppI18n } from '../i18n';

const StockTable = ({ stocks, loading, onViewDetail, onAnalyze }) => {
  const { language } = useAppI18n();
  const isEnglish = language === 'en-US';
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [sortField, setSortField] = useState('change_percent');
  const [sortDirection, setSortDirection] = useState('desc');
  const itemsPerPage = 10;

  const filteredStocks = stocks.filter(
    (stock) =>
      stock.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      stock.symbol.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const sortedStocks = [...filteredStocks].sort((a, b) => {
    const aValue = a[sortField];
    const bValue = b[sortField];
    return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
  });

  const totalPages = Math.ceil(sortedStocks.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedStocks = sortedStocks.slice(startIndex, startIndex + itemsPerPage);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
      return;
    }
    setSortField(field);
    setSortDirection('desc');
  };

  const renderSortIcon = (field) => {
    if (sortField !== field) return null;
    const Icon = sortDirection === 'asc' ? ArrowUp : ArrowDown;
    return <Icon size={12} className="ms-1" />;
  };

  if (loading) {
    return (
      <div className="text-center p-4">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">{isEnglish ? 'Loading...' : '加载中...'}</span>
        </div>
        <p className="mt-2">{isEnglish ? 'Loading stock data...' : '正在加载股票数据...'}</p>
      </div>
    );
  }

  return (
    <div>
      <InputGroup className="mb-3">
        <InputGroup.Text>
          <Search />
        </InputGroup.Text>
        <Form.Control
          placeholder={isEnglish ? 'Search by symbol or name...' : '搜索股票代码或名称...'}
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setCurrentPage(1);
          }}
        />
      </InputGroup>

      <div className="table-responsive">
        <Table striped hover className="stock-table">
          <thead className="table-dark">
            <tr>
              <th onClick={() => handleSort('symbol')} style={{ cursor: 'pointer' }}>
                {isEnglish ? 'Symbol' : '代码'} {renderSortIcon('symbol')}
              </th>
              <th onClick={() => handleSort('name')} style={{ cursor: 'pointer' }}>
                {isEnglish ? 'Name' : '名称'} {renderSortIcon('name')}
              </th>
              <th onClick={() => handleSort('price')} style={{ cursor: 'pointer' }}>
                {isEnglish ? 'Price' : '价格'} {renderSortIcon('price')}
              </th>
              <th onClick={() => handleSort('change')} style={{ cursor: 'pointer' }}>
                {isEnglish ? 'Change' : '涨跌额'} {renderSortIcon('change')}
              </th>
              <th onClick={() => handleSort('change_percent')} style={{ cursor: 'pointer' }}>
                {isEnglish ? 'Change %' : '涨跌幅'} {renderSortIcon('change_percent')}
              </th>
              <th onClick={() => handleSort('volume')} style={{ cursor: 'pointer' }}>
                {isEnglish ? 'Volume' : '成交量'} {renderSortIcon('volume')}
              </th>
              <th>{isEnglish ? 'Actions' : '操作'}</th>
            </tr>
          </thead>
          <tbody>
            {paginatedStocks.map((stock, index) => {
              const isPositive = stock.change >= 0;
              const badgeClass = isPositive ? 'bg-market-up' : 'bg-market-down';

              return (
                <tr key={stock.symbol || index} className="stock-row">
                  <td>
                    <strong>{stock.symbol}</strong>
                  </td>
                  <td>{stock.name}</td>
                  <td>
                    <span className="fw-bold">¥{stock.price.toFixed(2)}</span>
                  </td>
                  <td>
                    <Badge className={`d-inline-flex align-items-center ${badgeClass}`}>
                      {isPositive ? <ArrowUp size={10} className="me-1" /> : <ArrowDown size={10} className="me-1" />}
                      {isPositive ? '+' : ''}
                      {stock.change.toFixed(2)}
                    </Badge>
                  </td>
                  <td>
                    <Badge className={`d-inline-flex align-items-center ${badgeClass}`}>
                      {isPositive ? <GraphUp size={10} className="me-1" /> : <GraphDown size={10} className="me-1" />}
                      {isPositive ? '+' : ''}
                      {stock.change_percent.toFixed(2)}%
                    </Badge>
                  </td>
                  <td>{stock.volume.toLocaleString()}</td>
                  <td>
                    <div className="btn-group btn-group-sm" role="group">
                      <Button
                        variant="outline-primary"
                        size="sm"
                        onClick={() => onViewDetail(stock.symbol)}
                        title={isEnglish ? 'View Details' : '查看详情'}
                      >
                        <Eye size={14} />
                      </Button>
                      <Button
                        variant="outline-info"
                        size="sm"
                        onClick={() => onAnalyze(stock.symbol)}
                        title={isEnglish ? 'AI Analysis' : 'AI分析'}
                      >
                        <Cpu size={14} />
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </div>

      {totalPages > 1 && (
        <div className="d-flex justify-content-between align-items-center mt-3">
          <small className="text-muted">
            {isEnglish
              ? `Showing ${startIndex + 1} - ${Math.min(startIndex + itemsPerPage, sortedStocks.length)} of ${sortedStocks.length}`
              : `显示 ${startIndex + 1} - ${Math.min(startIndex + itemsPerPage, sortedStocks.length)} 条，共 ${sortedStocks.length} 条`}
          </small>
          <Pagination>
            <Pagination.Prev
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(currentPage - 1)}
            />
            {[...Array(totalPages)].map((_, index) => (
              <Pagination.Item
                key={index + 1}
                active={index + 1 === currentPage}
                onClick={() => setCurrentPage(index + 1)}
              >
                {index + 1}
              </Pagination.Item>
            ))}
            <Pagination.Next
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(currentPage + 1)}
            />
          </Pagination>
        </div>
      )}
    </div>
  );
};

export default StockTable;
