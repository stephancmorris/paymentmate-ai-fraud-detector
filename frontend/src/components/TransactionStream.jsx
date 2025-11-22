import { useCallback } from 'react';
import PropTypes from 'prop-types';
import { getTransactionHistory } from '../services/api';
import usePolling from '../hooks/usePolling';
import {
  formatCurrency,
  formatTimestamp,
  formatScore,
  getDecisionColor,
  getDecisionBackground,
  getScoreColor,
} from '../utils/formatters';

const styles = {
  container: {
    width: '100%',
    maxWidth: '1200px',
    margin: '0 auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1rem',
    padding: '1rem',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
  },
  title: {
    margin: 0,
    fontSize: '1.5rem',
    color: '#333',
  },
  stats: {
    display: 'flex',
    gap: '2rem',
    alignItems: 'center',
  },
  statItem: {
    textAlign: 'center',
  },
  statValue: {
    fontSize: '1.5rem',
    fontWeight: 'bold',
    color: '#333',
  },
  statLabel: {
    fontSize: '0.75rem',
    color: '#666',
    textTransform: 'uppercase',
  },
  lastUpdated: {
    fontSize: '0.8rem',
    color: '#666',
  },
  tableContainer: {
    overflowX: 'auto',
    backgroundColor: '#fff',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.9rem',
  },
  th: {
    padding: '12px 16px',
    textAlign: 'left',
    borderBottom: '2px solid #dee2e6',
    backgroundColor: '#f8f9fa',
    fontWeight: '600',
    color: '#495057',
    position: 'sticky',
    top: 0,
  },
  td: {
    padding: '12px 16px',
    borderBottom: '1px solid #dee2e6',
    verticalAlign: 'middle',
  },
  row: {
    cursor: 'pointer',
    transition: 'background-color 0.15s ease',
  },
  decision: {
    display: 'inline-block',
    padding: '4px 12px',
    borderRadius: '12px',
    fontSize: '0.75rem',
    fontWeight: 'bold',
    textTransform: 'uppercase',
  },
  score: {
    fontFamily: 'monospace',
    fontWeight: 'bold',
  },
  loading: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '4rem',
    color: '#666',
  },
  error: {
    padding: '2rem',
    textAlign: 'center',
    color: '#dc3545',
    backgroundColor: 'rgba(220, 53, 69, 0.1)',
    borderRadius: '8px',
    margin: '1rem 0',
  },
  errorButton: {
    marginTop: '1rem',
    padding: '8px 16px',
    backgroundColor: '#dc3545',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  empty: {
    padding: '4rem',
    textAlign: 'center',
    color: '#666',
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
};

const TransactionStream = ({ limit = 100, onTransactionClick }) => {
  const pollInterval = parseInt(import.meta.env.VITE_POLL_INTERVAL) || 2000;

  const fetchTransactions = useCallback(() => {
    return getTransactionHistory(limit);
  }, [limit]);

  const { data, loading, error, lastUpdated, refresh } = usePolling(
    fetchTransactions,
    pollInterval
  );

  const transactions = data?.transactions || [];
  const totalCount = data?.total_count || transactions.length;

  const flaggedCount = transactions.filter(
    (t) => t.decision === 'FLAG' || t.decision === 'DECLINE'
  ).length;

  if (loading && !data) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>
          <span>Loading transactions...</span>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div style={styles.container}>
        <div style={styles.error}>
          <p>Failed to load transactions: {error}</p>
          <button style={styles.errorButton} onClick={refresh}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>Live Transaction Stream</h2>
        <div style={styles.stats}>
          <div style={styles.statItem}>
            <div style={styles.statValue}>{totalCount}</div>
            <div style={styles.statLabel}>Total Transactions</div>
          </div>
          <div style={styles.statItem}>
            <div style={{ ...styles.statValue, color: '#dc3545' }}>{flaggedCount}</div>
            <div style={styles.statLabel}>Flagged</div>
          </div>
          <div>
            <button style={styles.refreshButton} onClick={refresh}>
              Refresh
            </button>
            {lastUpdated && (
              <div style={styles.lastUpdated}>
                Updated: {lastUpdated.toLocaleTimeString()}
              </div>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div style={{ ...styles.error, marginBottom: '1rem' }}>
          Connection error: {error}. Retrying...
        </div>
      )}

      {transactions.length === 0 ? (
        <div style={styles.empty}>
          <p>No transactions yet. Start the simulator to see live data.</p>
        </div>
      ) : (
        <div style={styles.tableContainer}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Time</th>
                <th style={styles.th}>User ID</th>
                <th style={styles.th}>Amount</th>
                <th style={styles.th}>Merchant</th>
                <th style={styles.th}>Category</th>
                <th style={styles.th}>Country</th>
                <th style={styles.th}>Score</th>
                <th style={styles.th}>Decision</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((txn, index) => (
                <tr
                  key={txn.request_id || index}
                  style={{
                    ...styles.row,
                    backgroundColor: getDecisionBackground(txn.decision),
                  }}
                  onClick={() => onTransactionClick?.(txn)}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#f0f0f0';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = getDecisionBackground(txn.decision);
                  }}
                >
                  <td style={styles.td}>{formatTimestamp(txn.timestamp)}</td>
                  <td style={styles.td}>{txn.user_id}</td>
                  <td style={styles.td}>{formatCurrency(txn.amount)}</td>
                  <td style={styles.td}>{txn.merchant_id}</td>
                  <td style={styles.td}>{txn.merchant_category}</td>
                  <td style={styles.td}>{txn.country || 'US'}</td>
                  <td style={{ ...styles.td, ...styles.score, color: getScoreColor(txn.score) }}>
                    {formatScore(txn.score)}
                  </td>
                  <td style={styles.td}>
                    <span
                      style={{
                        ...styles.decision,
                        color: getDecisionColor(txn.decision),
                        backgroundColor: getDecisionBackground(txn.decision),
                        border: `1px solid ${getDecisionColor(txn.decision)}`,
                      }}
                    >
                      {txn.decision}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

TransactionStream.propTypes = {
  limit: PropTypes.number,
  onTransactionClick: PropTypes.func,
};

export default TransactionStream;
