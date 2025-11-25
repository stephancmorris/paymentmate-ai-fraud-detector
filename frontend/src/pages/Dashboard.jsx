import { useNavigate } from 'react-router-dom';
import TransactionStream from '../components/TransactionStream';
import PerformanceMetrics from '../components/PerformanceMetrics';

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
    padding: '2rem',
  },
};

const Dashboard = () => {
  const navigate = useNavigate();

  const handleTransactionClick = (transaction) => {
    navigate('/investigation', { state: { transaction } });
  };

  return (
    <div style={styles.container}>
      <PerformanceMetrics pollInterval={10000} />
      <TransactionStream limit={100} onTransactionClick={handleTransactionClick} />
    </div>
  );
};

export default Dashboard;
