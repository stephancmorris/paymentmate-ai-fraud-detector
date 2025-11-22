export const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
};

export const formatTimestamp = (timestamp) => {
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

export const formatScore = (score) => {
  return (score * 100).toFixed(1) + '%';
};

export const getDecisionColor = (decision) => {
  switch (decision?.toUpperCase()) {
    case 'DECLINE':
      return '#dc3545';
    case 'FLAG':
      return '#ffc107';
    case 'ALLOW':
      return '#28a745';
    default:
      return '#6c757d';
  }
};

export const getDecisionBackground = (decision) => {
  switch (decision?.toUpperCase()) {
    case 'DECLINE':
      return 'rgba(220, 53, 69, 0.1)';
    case 'FLAG':
      return 'rgba(255, 193, 7, 0.1)';
    case 'ALLOW':
      return 'rgba(40, 167, 69, 0.05)';
    default:
      return 'transparent';
  }
};

export const getScoreColor = (score) => {
  if (score >= 0.9) return '#dc3545';
  if (score >= 0.5) return '#ffc107';
  return '#28a745';
};
