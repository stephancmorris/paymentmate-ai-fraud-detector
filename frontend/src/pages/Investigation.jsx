import { useLocation, useNavigate } from 'react-router-dom';
import ShapChart from '../components/ShapChart';
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
    maxWidth: '900px',
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
  gridThree: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
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
  modelInfo: {
    display: 'flex',
    justifyContent: 'center',
    gap: '2rem',
    marginTop: '1rem',
    paddingTop: '1rem',
    borderTop: '1px solid #dee2e6',
  },
  modelInfoItem: {
    textAlign: 'center',
  },
  modelInfoValue: {
    fontSize: '1rem',
    fontWeight: '600',
    color: '#333',
  },
  modelInfoLabel: {
    fontSize: '0.7rem',
    color: '#666',
    textTransform: 'uppercase',
  },
  featureList: {
    marginTop: '1.5rem',
    padding: '1rem',
    backgroundColor: '#fff',
    borderRadius: '4px',
    border: '1px solid #dee2e6',
  },
  featureListTitle: {
    fontSize: '0.85rem',
    fontWeight: '600',
    color: '#495057',
    marginBottom: '0.75rem',
  },
  featureItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0.5rem 0',
    borderBottom: '1px solid #f0f0f0',
  },
  featureName: {
    fontSize: '0.85rem',
    color: '#333',
  },
  featureValue: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
  },
  featureActual: {
    fontSize: '0.85rem',
    color: '#666',
    fontFamily: 'monospace',
  },
  featureShap: {
    fontSize: '0.85rem',
    fontWeight: 'bold',
    fontFamily: 'monospace',
    minWidth: '80px',
    textAlign: 'right',
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

  const hasExplanation = transaction.explanation && transaction.explanation.length > 0;

  const formatFeatureName = (name) => {
    return name
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (l) => l.toUpperCase());
  };

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

          {(transaction.model_version || transaction.inference_time_ms) && (
            <div style={styles.modelInfo}>
              {transaction.model_version && (
                <div style={styles.modelInfoItem}>
                  <div style={styles.modelInfoValue}>{transaction.model_version}</div>
                  <div style={styles.modelInfoLabel}>Model Version</div>
                </div>
              )}
              {transaction.inference_time_ms && (
                <div style={styles.modelInfoItem}>
                  <div style={styles.modelInfoValue}>{transaction.inference_time_ms.toFixed(2)}ms</div>
                  <div style={styles.modelInfoLabel}>Inference Time</div>
                </div>
              )}
              {transaction.features_used && (
                <div style={styles.modelInfoItem}>
                  <div style={styles.modelInfoValue}>{transaction.features_used}</div>
                  <div style={styles.modelInfoLabel}>Features Used</div>
                </div>
              )}
            </div>
          )}
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
            {hasExplanation ? (
              <>
                <ShapChart
                  explanations={transaction.explanation}
                  title="Top 5 Contributing Features"
                />

                <div style={styles.featureList}>
                  <div style={styles.featureListTitle}>Feature Details</div>
                  {transaction.explanation
                    .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
                    .map((exp, index) => (
                      <div
                        key={index}
                        style={{
                          ...styles.featureItem,
                          borderBottom: index < transaction.explanation.length - 1 ? '1px solid #f0f0f0' : 'none',
                        }}
                      >
                        <span style={styles.featureName}>{formatFeatureName(exp.feature_name)}</span>
                        <div style={styles.featureValue}>
                          <span style={styles.featureActual}>
                            Value: {typeof exp.feature_value === 'number' ? exp.feature_value.toFixed(2) : exp.feature_value ?? 'N/A'}
                          </span>
                          <span
                            style={{
                              ...styles.featureShap,
                              color: exp.shap_value > 0 ? '#dc3545' : '#28a745',
                            }}
                          >
                            {exp.shap_value > 0 ? '+' : ''}{exp.shap_value.toFixed(4)}
                          </span>
                        </div>
                      </div>
                    ))}
                </div>
              </>
            ) : (
              <p style={styles.shapNote}>
                No SHAP explanations available for this transaction.
                <br />
                SHAP values are generated when scoring transactions via the API.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Investigation;
