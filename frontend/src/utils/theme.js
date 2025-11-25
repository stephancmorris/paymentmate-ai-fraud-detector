// PaymentMate AI - Theme Constants
// Consistent color scheme and styling across the application

export const colors = {
  // Primary brand colors
  primary: '#2563eb', // Blue
  primaryHover: '#1d4ed8',
  primaryLight: '#dbeafe',

  // Decision colors
  success: '#28a745', // Green - ALLOW
  warning: '#ffc107', // Yellow - FLAG
  danger: '#dc3545', // Red - DECLINE
  info: '#17a2b8', // Cyan - Info

  // Background colors
  backgroundLight: '#f5f5f5',
  backgroundWhite: '#ffffff',
  backgroundGray: '#f8f9fa',

  // Text colors
  textPrimary: '#333333',
  textSecondary: '#666666',
  textMuted: '#888888',
  textLight: '#999999',

  // Border colors
  borderLight: '#dee2e6',
  borderMedium: '#ced4da',

  // State colors
  errorBackground: 'rgba(220, 53, 69, 0.1)',
  successBackground: 'rgba(40, 167, 69, 0.1)',
  warningBackground: 'rgba(255, 193, 7, 0.1)',
};

export const spacing = {
  xs: '0.25rem', // 4px
  sm: '0.5rem', // 8px
  md: '1rem', // 16px
  lg: '1.5rem', // 24px
  xl: '2rem', // 32px
  xxl: '3rem', // 48px
};

export const typography = {
  fontFamily: {
    base: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    mono: '"SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, "Courier New", monospace',
  },
  fontSize: {
    xs: '0.75rem', // 12px
    sm: '0.85rem', // 13.6px
    base: '1rem', // 16px
    lg: '1.125rem', // 18px
    xl: '1.25rem', // 20px
    xxl: '1.5rem', // 24px
    xxxl: '2rem', // 32px
  },
  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
  lineHeight: {
    tight: '1.25',
    normal: '1.5',
    relaxed: '1.75',
  },
};

export const shadows = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
  md: '0 2px 4px rgba(0, 0, 0, 0.1)',
  lg: '0 4px 6px rgba(0, 0, 0, 0.1)',
  xl: '0 10px 15px rgba(0, 0, 0, 0.1)',
};

export const borderRadius = {
  sm: '4px',
  md: '8px',
  lg: '12px',
  full: '9999px',
};

export const transitions = {
  fast: '150ms ease',
  base: '200ms ease',
  slow: '300ms ease',
};

export const breakpoints = {
  mobile: '480px',
  tablet: '768px',
  desktop: '1024px',
  wide: '1280px',
};

// Helper function to create responsive styles
export const mediaQuery = {
  mobile: `@media (max-width: ${breakpoints.mobile})`,
  tablet: `@media (max-width: ${breakpoints.tablet})`,
  desktop: `@media (min-width: ${breakpoints.desktop})`,
  wide: `@media (min-width: ${breakpoints.wide})`,
};

// Common component styles
export const commonStyles = {
  button: {
    base: {
      padding: `${spacing.sm} ${spacing.md}`,
      border: 'none',
      borderRadius: borderRadius.sm,
      cursor: 'pointer',
      fontSize: typography.fontSize.sm,
      fontWeight: typography.fontWeight.medium,
      transition: transitions.base,
      fontFamily: typography.fontFamily.base,
    },
    primary: {
      backgroundColor: colors.primary,
      color: colors.backgroundWhite,
    },
    secondary: {
      backgroundColor: colors.textSecondary,
      color: colors.backgroundWhite,
    },
    danger: {
      backgroundColor: colors.danger,
      color: colors.backgroundWhite,
    },
  },
  card: {
    backgroundColor: colors.backgroundWhite,
    borderRadius: borderRadius.md,
    padding: spacing.xl,
    boxShadow: shadows.md,
  },
  input: {
    padding: `${spacing.sm} ${spacing.md}`,
    border: `1px solid ${colors.borderLight}`,
    borderRadius: borderRadius.sm,
    fontSize: typography.fontSize.base,
    fontFamily: typography.fontFamily.base,
  },
};

export default {
  colors,
  spacing,
  typography,
  shadows,
  borderRadius,
  transitions,
  breakpoints,
  mediaQuery,
  commonStyles,
};
