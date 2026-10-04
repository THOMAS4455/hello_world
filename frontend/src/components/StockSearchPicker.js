import React, { useEffect, useId, useRef, useState } from 'react';
import { Form, ListGroup, Spinner } from 'react-bootstrap';
import stockApiService from '../services/stockApi';
import '../styles/StockSearchPicker.css';

const MIN_QUERY_LEN = 1;
const DEBOUNCE_MS = 350;
const MAX_RESULTS = 20;

const StockSearchPicker = ({
  value = '',
  onChange,
  onSelect,
  placeholder,
  disabled = false,
  isEnglish = false,
  excludeSymbols = [],
  hint,
}) => {
  const listId = useId();
  const wrapRef = useRef(null);
  const [query, setQuery] = useState(value);
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  useEffect(() => {
    setQuery(value);
  }, [value]);

  useEffect(() => {
    const keyword = query.trim();
    if (keyword.length < MIN_QUERY_LEN) {
      setResults([]);
      setSearching(false);
      setSearchError(null);
      return undefined;
    }

    setSearching(true);
    setSearchError(null);
    const timer = setTimeout(async () => {
      try {
        const stocks = await stockApiService.searchStocks(keyword);
        const excluded = new Set((excludeSymbols || []).map((s) => String(s)));
        const filtered = (stocks || [])
          .filter((item) => item?.symbol && !excluded.has(String(item.symbol)))
          .slice(0, MAX_RESULTS);
        setResults(filtered);
        setOpen(true);
        setActiveIndex(filtered.length > 0 ? 0 : -1);
      } catch (e) {
        setResults([]);
        setSearchError(e.message);
      } finally {
        setSearching(false);
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [query, excludeSymbols]);

  useEffect(() => {
    const handleOutside = (event) => {
      if (wrapRef.current && !wrapRef.current.contains(event.target)) {
        setOpen(false);
        setActiveIndex(-1);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  const pickStock = (stock) => {
    if (!stock?.symbol) {
      return;
    }
    const label = `${stock.symbol} ${stock.name || ''}`.trim();
    setQuery(label);
    setOpen(false);
    setResults([]);
    setActiveIndex(-1);
    onChange?.(label);
    onSelect?.(stock);
  };

  const handleKeyDown = (event) => {
    if (!open || results.length === 0) {
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((idx) => Math.min(results.length - 1, idx + 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((idx) => Math.max(0, idx - 1));
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault();
      pickStock(results[activeIndex]);
    } else if (event.key === 'Escape') {
      setOpen(false);
      setActiveIndex(-1);
    }
  };

  const defaultPlaceholder = isEnglish
    ? 'Search by name or symbol, e.g. Ping An or 000001'
    : '输入名称或代码搜索，如 平安银行 或 000001';

  return (
    <div className="stock-search-picker" ref={wrapRef}>
      <Form.Control
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          onChange?.(e.target.value);
          if (e.target.value.trim()) {
            setOpen(true);
          }
        }}
        onFocus={() => {
          if (results.length > 0) {
            setOpen(true);
          }
        }}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || defaultPlaceholder}
        disabled={disabled}
        autoComplete="off"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
      />
      {searching && (
        <div className="stock-search-picker-meta">
          <Spinner animation="border" size="sm" className="me-2" />
          {isEnglish ? 'Searching...' : '搜索中...'}
        </div>
      )}
      {!searching && searchError && (
        <div className="stock-search-picker-meta text-danger">{searchError}</div>
      )}
      {!searching && !searchError && query.trim() && results.length === 0 && open && (
        <div className="stock-search-picker-meta text-muted">
          {isEnglish ? 'No matching stocks.' : '未找到匹配股票。'}
        </div>
      )}
      {!searching && open && results.length > 0 && (
        <ListGroup id={listId} className="stock-search-picker-list" role="listbox">
          {results.map((item, index) => (
            <ListGroup.Item
              key={`${item.symbol}-${item.name || ''}`}
              action
              active={index === activeIndex}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => pickStock(item)}
              role="option"
              aria-selected={index === activeIndex}
            >
              <div className="stock-search-picker-row">
                <strong>{item.symbol}</strong>
                <span className="text-muted">{item.name || (isEnglish ? 'Unknown' : '未知')}</span>
              </div>
              {item.formattedPrice && (
                <div className="small text-muted">{item.formattedPrice}</div>
              )}
            </ListGroup.Item>
          ))}
        </ListGroup>
      )}
      {hint && <Form.Text className="text-muted">{hint}</Form.Text>}
    </div>
  );
};

export default StockSearchPicker;
