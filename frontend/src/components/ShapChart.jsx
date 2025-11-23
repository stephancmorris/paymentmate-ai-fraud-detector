import PropTypes from 'prop-types';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';

const styles = {
  container: {
    width: '100%',
    padding: '1rem 0',
  },
  title: {
    fontSize: '1rem',
    fontWeight: '600',
    marginBottom: '1rem',
    color: '#333',
  },
  legend: {
    display: 'flex',
    justifyContent: 'center',
    gap: '2rem',
    marginTop: '1rem',
    fontSize: '0.85rem',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  legendDot: {
    width: '12px',
    height: '12px',
    borderRadius: '2px',
  },
  noData: {
    textAlign: 'center',
    padding: '2rem',
    color: '#666',
    fontStyle: 'italic',
  },
};

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const isPositive = data.shap_value > 0;

    return (
      <div
        style={{
          backgroundColor: '#fff',
          border: '1px solid #ccc',
          borderRadius: '4px',
          padding: '12px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        }}
      >
        <p style={{ margin: '0 0 8px 0', fontWeight: 'bold' }}>{data.feature_name}</p>
        <p style={{ margin: '0 0 4px 0', color: '#666' }}>
          Feature Value: <strong>{typeof data.feature_value === 'number' ? data.feature_value.toFixed(2) : data.feature_value}</strong>
        </p>
        <p style={{ margin: '0', color: isPositive ? '#dc3545' : '#28a745' }}>
          SHAP Impact: <strong>{isPositive ? '+' : ''}{data.shap_value.toFixed(4)}</strong>
        </p>
        <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#888' }}>
          {isPositive ? '↑ Increases fraud risk' : '↓ Decreases fraud risk'}
        </p>
      </div>
    );
  }
  return null;
};

CustomTooltip.propTypes = {
  active: PropTypes.bool,
  payload: PropTypes.array,
};

const ShapChart = ({ explanations, title = 'Feature Contributions (SHAP Values)' }) => {
  if (!explanations || explanations.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.noData}>
          No SHAP explanations available for this transaction.
        </div>
      </div>
    );
  }

  const sortedData = [...explanations]
    .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
    .slice(0, 5);

  const formatFeatureName = (name) => {
    return name
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (l) => l.toUpperCase());
  };

  const chartData = sortedData.map((item) => ({
    ...item,
    displayName: formatFeatureName(item.feature_name),
    absValue: Math.abs(item.shap_value),
  }));

  const maxAbsValue = Math.max(...chartData.map((d) => Math.abs(d.shap_value)));
  const domainPadding = maxAbsValue * 0.1;

  return (
    <div style={styles.container}>
      {title && <h4 style={styles.title}>{title}</h4>}

      <ResponsiveContainer width="100%" height={250}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 10, right: 30, left: 120, bottom: 10 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
          <XAxis
            type="number"
            domain={[-maxAbsValue - domainPadding, maxAbsValue + domainPadding]}
            tickFormatter={(value) => value.toFixed(2)}
          />
          <YAxis
            type="category"
            dataKey="displayName"
            width={110}
            tick={{ fontSize: 12 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine x={0} stroke="#666" strokeWidth={2} />
          <Bar dataKey="shap_value" barSize={24}>
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.shap_value > 0 ? '#dc3545' : '#28a745'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div style={styles.legend}>
        <div style={styles.legendItem}>
          <div style={{ ...styles.legendDot, backgroundColor: '#dc3545' }} />
          <span>Increases Fraud Risk</span>
        </div>
        <div style={styles.legendItem}>
          <div style={{ ...styles.legendDot, backgroundColor: '#28a745' }} />
          <span>Decreases Fraud Risk</span>
        </div>
      </div>
    </div>
  );
};

ShapChart.propTypes = {
  explanations: PropTypes.arrayOf(
    PropTypes.shape({
      feature_name: PropTypes.string.isRequired,
      feature_value: PropTypes.number,
      shap_value: PropTypes.number.isRequired,
      contribution: PropTypes.string,
    })
  ),
  title: PropTypes.string,
};

export default ShapChart;
