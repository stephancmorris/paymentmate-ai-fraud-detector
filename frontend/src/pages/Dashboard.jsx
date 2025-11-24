import { useNavigate } from 'react-router-dom';
import TransactionStream from '../components/TransactionStream';
import PerformanceMetrics from '../components/PerformanceMetrics';

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
    padding: '2rem',
  },
  header: {
    textAlign: 'center',
    marginBottom: '2rem',
  },
  title: {
    fontSize: '2rem',
    color: '#333',
    margin: '0 0 0.5rem 0',
  },
  subtitle: {
    color: '#666',
    margin: 0,
  },
};

const Dashboard = () => {
  const navigate = useNavigate();

  const handleTransactionClick = (transaction) => {
    navigate('/investigation', { state: { transaction } });
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>PaymentMate AI</h1>
        <p style={styles.subtitle}>Real-Time Fraud Detection Dashboard</p>
      </header>

      <PerformanceMetrics pollInterval={10000} />

      <TransactionStream limit={100} onTransactionClick={handleTransactionClick} />
    </div>
  );
};

export default Dashboard;
