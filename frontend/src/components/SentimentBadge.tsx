import React from 'react';
import { ThumbsUp, ThumbsDown, Minus, Split } from 'lucide-react';

interface Props {
  sentiment: string;
  detail?: string;
  confidence?: number;
  isMixed?: boolean;
  showConfidence?: boolean;
}

export const SentimentBadge: React.FC<Props> = ({
  sentiment,
  detail,
  confidence,
  isMixed = false,
  showConfidence = true,
}) => {
  const normSentiment = (sentiment || 'Neutral').toLowerCase();

  let className = 'badge-sentiment neutral';
  let Icon = Minus;
  let labelText = detail || sentiment || 'Neutral';

  if (isMixed || normSentiment.includes('mixed') || (detail && detail.includes('Mixed'))) {
    className = 'badge-sentiment mixed';
    Icon = Split;
    labelText = 'Neutral (Mixed)';
  } else if (normSentiment === 'positive') {
    className = 'badge-sentiment positive';
    Icon = ThumbsUp;
    labelText = 'Positive';
  } else if (normSentiment === 'negative') {
    className = 'badge-sentiment negative';
    Icon = ThumbsDown;
    labelText = 'Negative';
  }

  return (
    <span className={className} title={detail || sentiment}>
      <Icon size={12} strokeWidth={2.5} />
      <span>{labelText}</span>
      {showConfidence && confidence !== undefined && confidence > 0 && (
        <span style={{ opacity: 0.85, fontWeight: 500, fontSize: '0.72rem', marginLeft: '2px' }}>
          ({Math.round(confidence * 100)}%)
        </span>
      )}
    </span>
  );
};
