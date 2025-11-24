import { useCallback, useState } from 'react';
import PropTypes from 'prop-types';
import { getMetrics } from '../services/api';
import usePolling from '../hooks/usePolling';

const styles = {
  container: {
    width: '100%',
    maxWidth: '1200px',
    margin: '0 auto',
    marginBottom: '2rem',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1rem',
  },
  title: {
    margin: 0,
    fontSize: '1.25rem',
    color: '#333',
  },
  refreshButton: {
    padding: '6px 12px',
    backgroundColor: '#007bff',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.85rem',
  },
  lastUpdated: {
    fontSize: '0.75rem',
    color: '#666',
    marginTop: '4px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '1rem',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: '8px',
    padding: '1.5rem',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    textAlign: 'center',
  },
  cardTitle: {
    fontSize: '0.75rem',
    color: '#666',
    textTransform: 'uppercase',
    marginBottom: '0.5rem',
  },
  cardValue: {
    fontSize: '2rem',
    fontWeight: 'bold',
    color: '#333',
    marginBottom: '0.25rem',
  },
  cardSubtext: {
    fontSize: '0.8rem',
    color: '#888',
  },
  progressContainer: {
    marginTop: '0.75rem',
  },
  progressBar: {
    width: '100%',
    height: '8px',
    backgroundColor: '#e9ecef',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    borderRadius: '4px',
    transition: 'width 0.3s ease',
  },
  loading: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '2rem',
    color: '#666',
  },
  error: {
    padding: '1rem',
    textAlign: 'center',
    color: '#dc3545',
    backgroundColor: 'rgba(220, 53, 69, 0.1)',
    borderRadius: '8px',
  },
  errorButton: {
    marginTop: '0.5rem',
    padding: '6px 12px',
    backgroundColor: '#dc3545',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '0.85rem',
  },
};

const getProgressColor = (value, type) => {
  if (type === 'precision' || type === 'recall' || type === 'f1') {
    if (value >= 0.8) return '#28a745';
    if (value >= 0.6) return '#ffc107';
    return '#dc3545';
  }
  return '#007bff';
};

const formatPercentage = (value) => {
  if (value === null || value === undefined) return 'N/A';
  return `${(value * 100).toFixed(1)}%`;
};

const formatNumber = (value) => {
  if (value === null || value === undefined) return '0';
  return new Intl.NumberFormat('en-US').format(Math.round(value));
};

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '$0';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

const MetricCard = ({ title, value, subtext, showProgress, progressValue, progressType }) => (
  <div style={styles.card}>
    <div style={styles.cardTitle}>{title}</div>
    <div style={styles.cardValue}>{value}</div>
    {subtext && <div style={styles.cardSubtext}>{subtext}</div>}
    {showProgress && (
      <div style={styles.progressContainer}>
        <div style={styles.progressBar}>
          <div
            style={{
              ...styles.progressFill,
              width: `${Math.min(100, (progressValue || 0) * 100)}%`,
              backgroundColor: getProgressColor(progressValue, progressType),
            }}
          />
        </div>
      </div>
    )}
  </div>
);

MetricCard.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
  subtext: PropTypes.string,
  showProgress: PropTypes.bool,
  progressValue: PropTypes.number,
  progressType: PropTypes.string,
};

const PerformanceMetrics = ({ pollInterval = 10000, showTitle = true }) => {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchMetrics = useCallback(() => {
    return getMetrics();
  }, []);

  const { data, loading, error, lastUpdated, refresh } = usePolling(
    fetchMetrics,
    pollInterval
  );

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refresh();
    setIsRefreshing(false);
  };

  if (loading && !data) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>Loading metrics...</div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div style={styles.container}>
        <div style={styles.error}>
          <p>Failed to load metrics: {error}</p>
          <button style={styles.errorButton} onClick={handleRefresh}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  const metrics = data || {};
  const precision = metrics.precision ?? 0;
  const recall = metrics.recall ?? 0;
  const f1Score = metrics.f1_score ?? 0;
  const totalTransactions = metrics.total_transactions ?? 0;
  const flaggedCount = metrics.flagged_count ?? 0;
  const allowedCount = metrics.allowed_count ?? 0;
  const lossesPrevented = metrics.losses_prevented ?? 0;
  const averageLatency = metrics.average_latency_ms ?? 0;

  return (
    <div style={styles.container}>
      {showTitle && (
        <div style={styles.header}>
          <div>
            <h3 style={styles.title}>Model Performance</h3>
            {lastUpdated && (
              <div style={styles.lastUpdated}>
                Last updated: {lastUpdated.toLocaleTimeString()}
              </div>
            )}
          </div>
          <button
            style={{
              ...styles.refreshButton,
              opacity: isRefreshing ? 0.7 : 1,
            }}
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      )}

      {error && (
        <div style={{ ...styles.error, marginBottom: '1rem', fontSize: '0.85rem' }}>
          Connection error: {error}. Showing cached data.
        </div>
      )}

      <div style={styles.grid}>
        <MetricCard
          title="Precision"
          value={formatPercentage(precision)}
          subtext="True positives / All flagged"
          showProgress
          progressValue={precision}
          progressType="precision"
        />
        <MetricCard
          title="Recall"
          value={formatPercentage(recall)}
          subtext="True positives / All fraud"
          showProgress
          progressValue={recall}
          progressType="recall"
        />
        <MetricCard
          title="F1 Score"
          value={formatPercentage(f1Score)}
          subtext="Harmonic mean of P & R"
          showProgress
          progressValue={f1Score}
          progressType="f1"
        />
        <MetricCard
          title="Total Transactions"
          value={formatNumber(totalTransactions)}
          subtext={`${formatNumber(flaggedCount)} flagged, ${formatNumber(allowedCount)} allowed`}
        />
        <MetricCard
          title="Losses Prevented"
          value={formatCurrency(lossesPrevented)}
          subtext="Estimated fraud stopped"
        />
        <MetricCard
          title="Avg Latency"
          value={`${averageLatency.toFixed(1)}ms`}
          subtext="Average scoring time"
        />
      </div>
    </div>
  );
};

PerformanceMetrics.propTypes = {
  pollInterval: PropTypes.number,
  showTitle: PropTypes.bool,
};

export default PerformanceMetrics;
