import { Link, useLocation } from 'react-router-dom';
import { colors, spacing, typography, borderRadius, shadows } from '../utils/theme';

const styles = {
  nav: {
    backgroundColor: colors.backgroundWhite,
    boxShadow: shadows.md,
    position: 'sticky',
    top: 0,
    zIndex: 1000,
  },
  container: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: `${spacing.md} ${spacing.xl}`,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: spacing.md,
    textDecoration: 'none',
  },
  logo: {
    fontSize: typography.fontSize.xxl,
    fontWeight: typography.fontWeight.bold,
    color: colors.primary,
    margin: 0,
  },
  subtitle: {
    fontSize: typography.fontSize.sm,
    color: colors.textSecondary,
    margin: 0,
  },
  links: {
    display: 'flex',
    gap: spacing.lg,
    alignItems: 'center',
  },
  link: {
    textDecoration: 'none',
    color: colors.textSecondary,
    fontSize: typography.fontSize.base,
    fontWeight: typography.fontWeight.medium,
    padding: `${spacing.sm} ${spacing.md}`,
    borderRadius: borderRadius.sm,
    transition: 'all 200ms ease',
  },
  linkActive: {
    color: colors.primary,
    backgroundColor: colors.primaryLight,
  },
  linkHover: {
    color: colors.textPrimary,
    backgroundColor: colors.backgroundGray,
  },
};

const Navigation = () => {
  const location = useLocation();

  const isActive = (path) => {
    return location.pathname === path;
  };

  return (
    <nav style={styles.nav} role="navigation" aria-label="Main navigation">
      <div style={styles.container}>
        <Link to="/" style={styles.brand} aria-label="PaymentMate AI Home">
          <div>
            <h1 style={styles.logo}>PaymentMate AI</h1>
            <p style={styles.subtitle}>Real-Time Fraud Detection</p>
          </div>
        </Link>

        <div style={styles.links}>
          <Link
            to="/"
            style={{
              ...styles.link,
              ...(isActive('/') ? styles.linkActive : {}),
            }}
            onMouseEnter={(e) => {
              if (!isActive('/')) {
                Object.assign(e.target.style, styles.linkHover);
              }
            }}
            onMouseLeave={(e) => {
              if (!isActive('/')) {
                e.target.style.color = colors.textSecondary;
                e.target.style.backgroundColor = 'transparent';
              }
            }}
            aria-current={isActive('/') ? 'page' : undefined}
          >
            Dashboard
          </Link>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
