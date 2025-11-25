import PropTypes from 'prop-types';
import { colors, spacing, typography, borderRadius } from '../utils/theme';

const styles = {
  container: {
    padding: spacing.lg,
    textAlign: 'center',
    color: colors.danger,
    backgroundColor: colors.errorBackground,
    borderRadius: borderRadius.md,
    border: `1px solid ${colors.danger}`,
  },
  title: {
    margin: '0 0 ' + spacing.sm + ' 0',
    fontSize: typography.fontSize.lg,
    fontWeight: typography.fontWeight.semibold,
  },
  message: {
    margin: '0 0 ' + spacing.md + ' 0',
    fontSize: typography.fontSize.base,
    color: colors.textPrimary,
  },
  button: {
    padding: `${spacing.sm} ${spacing.md}`,
    backgroundColor: colors.danger,
    color: colors.backgroundWhite,
    border: 'none',
    borderRadius: borderRadius.sm,
    cursor: 'pointer',
    fontSize: typography.fontSize.sm,
    fontWeight: typography.fontWeight.medium,
    transition: 'background-color 200ms ease',
  },
  buttonHover: {
    backgroundColor: '#c82333',
  },
};

const ErrorMessage = ({ title = 'Error', message, onRetry, retryText = 'Retry' }) => {
  return (
    <div style={styles.container} role="alert">
      <h3 style={styles.title}>{title}</h3>
      {message && <p style={styles.message}>{message}</p>}
      {onRetry && (
        <button
          style={styles.button}
          onClick={onRetry}
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = styles.buttonHover.backgroundColor;
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = colors.danger;
          }}
        >
          {retryText}
        </button>
      )}
    </div>
  );
};

ErrorMessage.propTypes = {
  title: PropTypes.string,
  message: PropTypes.string,
  onRetry: PropTypes.func,
  retryText: PropTypes.string,
};

export default ErrorMessage;
