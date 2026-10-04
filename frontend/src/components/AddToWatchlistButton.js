import React, { useEffect, useState } from 'react';
import { Button, Spinner } from 'react-bootstrap';
import { useWatchlist } from '../hooks/useWatchlist';

const AddToWatchlistButton = ({
  symbol,
  size = 'sm',
  variant = 'outline-success',
  className = '',
  isEnglish = false,
  watchlistApi = null,
}) => {
  const internal = useWatchlist({ autoLoad: !watchlistApi });
  const api = watchlistApi || internal;
  const { isInWatchlist, addSymbol, mutating, loading } = api;

  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    if (!feedback) {
      return undefined;
    }
    const timer = setTimeout(() => setFeedback(null), 2200);
    return () => clearTimeout(timer);
  }, [feedback]);

  if (!symbol) {
    return null;
  }

  const inList = isInWatchlist(symbol);

  const handleClick = async () => {
    if (inList || mutating) {
      return;
    }
    try {
      const result = await addSymbol(symbol);
      if (result.ok) {
        setFeedback(isEnglish ? 'Added' : '已加入');
      } else if (result.reason === 'duplicate') {
        setFeedback(isEnglish ? 'In watchlist' : '已在自选');
      } else if (result.reason === 'limit') {
        setFeedback(isEnglish ? 'Limit 20' : '已满20只');
      } else if (result.reason === 'invalid') {
        setFeedback(isEnglish ? 'Invalid code' : '代码无效');
      }
    } catch {
      setFeedback(isEnglish ? 'Failed' : '添加失败');
    }
  };

  const label = feedback
    || (inList
      ? (isEnglish ? 'In watchlist' : '已在自选')
      : (isEnglish ? 'Add to watchlist' : '加入自选'));

  return (
    <Button
      variant={inList ? 'success' : variant}
      size={size}
      className={className}
      onClick={handleClick}
      disabled={loading || mutating || inList}
      title={isEnglish ? 'Add to investment watchlist' : '加入投资中心自选池'}
    >
      {(mutating && !inList) ? <Spinner animation="border" size="sm" className="me-1" /> : null}
      {inList ? '★ ' : '+ '}
      {label}
    </Button>
  );
};

export default AddToWatchlistButton;
