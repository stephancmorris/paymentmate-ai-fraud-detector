import PropTypes from 'prop-types';
import { colors, spacing, typography } from '../utils/theme';

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xxl,
    color: colors.textSecondary,
  },
  spinner: {
    width: '48px',
    height: '48px',
    border: `4px solid ${colors.borderLight}`,
    borderTop: `4px solid ${colors.primary}`,
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  message: {
    marginTop: spacing.md,
    fontSize: typography.fontSize.base,
    color: colors.textSecondary,
  },
};

// Add keyframe animation to document
if (typeof document !== 'undefined') {
  const styleSheet = document.styleSheets[0];
  const keyframes = `
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
  `;

  try {
    styleSheet.insertRule(keyframes, styleSheet.cssRules.length);
  } catch (e) {
    // Rule may already exist
  }
}

const LoadingSpinner = ({ message = 'Loading...', size = 'medium' }) => {
  const sizeMap = {
    small: '32px',
    medium: '48px',
    large: '64px',
  };

  return (
    <div style={styles.container} role="status" aria-live="polite">
      <div
        style={{
          ...styles.spinner,
          width: sizeMap[size],
          height: sizeMap[size],
        }}
        aria-hidden="true"
      />
      {message && <p style={styles.message}>{message}</p>}
      <span className="sr-only">{message}</span>
    </div>
  );
};

LoadingSpinner.propTypes = {
  message: PropTypes.string,
  size: PropTypes.oneOf(['small', 'medium', 'large']),
};

export default LoadingSpinner;
