import { useLocation, useNavigate } from 'react-router-dom';
import {
  formatCurrency,
  formatTimestamp,
  formatScore,
  getDecisionColor,
  getScoreColor,
} from '../utils/formatters';

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
    padding: '2rem',
  },
  backButton: {
    padding: '8px 16px',
    backgroundColor: '#6c757d',
    color: '#fff',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    marginBottom: '1rem',
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: '8px',
    padding: '2rem',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    maxWidth: '800px',
    margin: '0 auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '2rem',
    paddingBottom: '1rem',
    borderBottom: '2px solid #dee2e6',
  },
  title: {
    margin: 0,
    fontSize: '1.5rem',
    color: '#333',
  },
  decision: {
    padding: '8px 16px',
    borderRadius: '20px',
    fontSize: '0.9rem',
    fontWeight: 'bold',
    textTransform: 'uppercase',
  },
  section: {
    marginBottom: '2rem',
  },
  sectionTitle: {
    fontSize: '1.1rem',
    fontWeight: '600',
    color: '#495057',
    marginBottom: '1rem',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '1rem',
  },
  field: {
    padding: '1rem',
    backgroundColor: '#f8f9fa',
    borderRadius: '4px',
  },
  fieldLabel: {
    fontSize: '0.75rem',
    color: '#666',
    textTransform: 'uppercase',
    marginBottom: '0.25rem',
  },
  fieldValue: {
    fontSize: '1.1rem',
    fontWeight: '500',
    color: '#333',
  },
  scoreContainer: {
    textAlign: 'center',
    padding: '2rem',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
    marginBottom: '2rem',
  },
  scoreValue: {
    fontSize: '3rem',
    fontWeight: 'bold',
    marginBottom: '0.5rem',
  },
  scoreLabel: {
    fontSize: '0.9rem',
    color: '#666',
  },
  placeholder: {
    textAlign: 'center',
    padding: '4rem',
    color: '#666',
  },
  shapSection: {
    backgroundColor: '#f8f9fa',
    padding: '1.5rem',
    borderRadius: '8px',
  },
  shapNote: {
    color: '#666',
    fontStyle: 'italic',
    textAlign: 'center',
  },
};

const Investigation = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const transaction = location.state?.transaction;

  if (!transaction) {
    return (
      <div style={styles.container}>
        <button style={styles.backButton} onClick={() => navigate('/')}>
          ← Back to Dashboard
        </button>
        <div style={styles.card}>
          <div style={styles.placeholder}>
            <h2>No Transaction Selected</h2>
            <p>Click on a transaction from the dashboard to view details.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <button style={styles.backButton} onClick={() => navigate('/')}>
        ← Back to Dashboard
      </button>

      <div style={styles.card}>
        <div style={styles.header}>
          <h1 style={styles.title}>Transaction Investigation</h1>
          <span
            style={{
              ...styles.decision,
              color: getDecisionColor(transaction.decision),
              backgroundColor: `${getDecisionColor(transaction.decision)}20`,
              border: `2px solid ${getDecisionColor(transaction.decision)}`,
            }}
          >
            {transaction.decision}
          </span>
        </div>

        <div style={styles.scoreContainer}>
          <div style={{ ...styles.scoreValue, color: getScoreColor(transaction.score) }}>
            {formatScore(transaction.score)}
          </div>
          <div style={styles.scoreLabel}>Fraud Risk Score</div>
        </div>

        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Transaction Details</h3>
          <div style={styles.grid}>
            <div style={styles.field}>
              <div style={styles.fieldLabel}>Amount</div>
              <div style={styles.fieldValue}>{formatCurrency(transaction.amount)}</div>
            </div>
            <div style={styles.field}>
              <div style={styles.fieldLabel}>Timestamp</div>
              <div style={styles.fieldValue}>{formatTimestamp(transaction.timestamp)}</div>
            </div>
            <div style={styles.field}>
              <div style={styles.fieldLabel}>User ID</div>
              <div style={styles.fieldValue}>{transaction.user_id}</div>
            </div>
            <div style={styles.field}>
              <div style={styles.fieldLabel}>Merchant</div>
              <div style={styles.fieldValue}>{transaction.merchant_id}</div>
            </div>
            <div style={styles.field}>
              <div style={styles.fieldLabel}>Category</div>
              <div style={styles.fieldValue}>{transaction.merchant_category}</div>
            </div>
            <div style={styles.field}>
              <div style={styles.fieldLabel}>Country</div>
              <div style={styles.fieldValue}>{transaction.country || 'US'}</div>
            </div>
            <div style={styles.field}>
              <div style={styles.fieldLabel}>Payment Method</div>
              <div style={styles.fieldValue}>{transaction.payment_method || 'credit_card'}</div>
            </div>
            <div style={styles.field}>
              <div style={styles.fieldLabel}>Request ID</div>
              <div style={{ ...styles.fieldValue, fontSize: '0.85rem', fontFamily: 'monospace' }}>
                {transaction.request_id || 'N/A'}
              </div>
            </div>
          </div>
        </div>

        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>SHAP Explanation</h3>
          <div style={styles.shapSection}>
            {transaction.explanation && transaction.explanation.length > 0 ? (
              <div>
                {transaction.explanation.map((exp, index) => (
                  <div
                    key={index}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: '0.5rem 0',
                      borderBottom: index < transaction.explanation.length - 1 ? '1px solid #dee2e6' : 'none',
                    }}
                  >
                    <span>{exp.feature_name}</span>
                    <span
                      style={{
                        fontWeight: 'bold',
                        color: exp.contribution === 'fraud' ? '#dc3545' : '#28a745',
                      }}
                    >
                      {exp.shap_value > 0 ? '+' : ''}
                      {exp.shap_value.toFixed(4)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p style={styles.shapNote}>
                SHAP explanations will appear here when available.
                <br />
                (Coming in Story 4.3)
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Investigation;
