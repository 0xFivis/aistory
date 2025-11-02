/*
 * Design tokens for the aistory frontend.
 * All values are expressed as plain objects so they can be imported in Vue components,
 * Tailwind/Windi configuration, or Element Plus theme overrides.
 */

export const colorPalette = {
  primary: '#2563eb',
  primaryHover: '#1d4ed8',
  primaryActive: '#1e40af',
  primarySoft: '#dbeafe',
  accent: '#f97316',
  accentSoft: '#ffedd5',
  success: '#16a34a',
  warning: '#f59e0b',
  danger: '#dc2626',
  info: '#0ea5e9',
  neutral100: '#f9fafb',
  neutral200: '#f3f4f6',
  neutral300: '#e5e7eb',
  neutral400: '#d1d5db',
  neutral500: '#9ca3af',
  neutral600: '#6b7280',
  neutral700: '#4b5563',
  neutral800: '#374151',
  neutral900: '#111827',
  backgroundPage: '#f5f7fb',
  backgroundCard: '#ffffff',
  borderSubtle: '#e5e7eb',
  borderStrong: '#d1d5db',
  overlay: 'rgba(17, 24, 39, 0.55)'
} as const

export const typography = {
  fontFamilyBase: "'Inter', 'PingFang SC', 'Microsoft Yahei', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  fontFamilyMono: "'JetBrains Mono', 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace",
  fontSizeXs: '12px',
  fontSizeSm: '13px',
  fontSizeMd: '14px',
  fontSizeLg: '16px',
  fontSizeXl: '18px',
  fontSizeDisplay: '24px',
  lineHeightTight: 1.25,
  lineHeightBase: 1.5,
  lineHeightLoose: 1.7,
  fontWeightRegular: 400,
  fontWeightMedium: 500,
  fontWeightSemibold: 600,
  fontWeightBold: 700
} as const

export const spacing = {
  px: '1px',
  '0': '0px',
  '1': '4px',
  '2': '8px',
  '3': '12px',
  '4': '16px',
  '5': '20px',
  '6': '24px',
  '8': '32px',
  '10': '40px',
  '12': '48px',
  '14': '56px',
  '16': '64px'
} as const

export const radii = {
  none: '0px',
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  pill: '999px'
} as const

export const shadows = {
  subtle: '0 1px 2px rgba(15, 23, 42, 0.06)',
  card: '0 8px 24px rgba(15, 23, 42, 0.08)',
  overlay: '0 20px 45px rgba(15, 23, 42, 0.15)'
} as const

export const transitions = {
  base: 'all 150ms ease-in-out',
  emphasized: 'all 220ms cubic-bezier(0.4, 0, 0.2, 1)'
} as const

export const layout = {
  pageMaxWidth: '1280px',
  sidebarWidth: '260px',
  headerHeight: '64px',
  sectionGap: spacing['6'],
  cardPadding: spacing['4']
} as const

export const componentTokens = {
  button: {
    heightSm: '28px',
    heightMd: '36px',
    heightLg: '44px',
    horizontalPaddingSm: spacing['2'],
    horizontalPaddingMd: spacing['3'],
    horizontalPaddingLg: spacing['4'],
    borderRadius: radii.md,
    fontWeight: typography.fontWeightMedium,
    transition: transitions.base
  },
  card: {
    borderRadius: radii.lg,
    background: colorPalette.backgroundCard,
    borderColor: colorPalette.borderSubtle,
    shadow: shadows.card,
    padding: spacing['4'],
    headerSpacing: spacing['3']
  },
  table: {
    headerBackground: colorPalette.neutral100,
    rowHover: '#f0f5ff',
    borderColor: colorPalette.borderSubtle,
    headerTextColor: colorPalette.neutral700,
    bodyTextColor: colorPalette.neutral800,
    zebraBackground: '#f8fbff'
  },
  dialog: {
    maxWidth: '720px',
    borderRadius: radii.lg,
    padding: spacing['5'],
    headerFontSize: typography.fontSizeXl,
    backdrop: colorPalette.overlay
  },
  form: {
    labelColor: colorPalette.neutral700,
    helperColor: colorPalette.neutral600,
    controlBorderRadius: radii.md,
    controlBorderColor: colorPalette.borderSubtle,
    controlFocusBorder: colorPalette.primary,
    sectionGap: spacing['5']
  },
  tag: {
    borderRadius: radii.pill,
    height: '24px',
    fontSize: typography.fontSizeSm,
    paddingInline: spacing['2']
  }
} as const

export const elevation = {
  borderRadiusDefault: radii.lg,
  cardShadow: shadows.card,
  surfaceBackground: colorPalette.backgroundCard,
  surfaceBorder: colorPalette.borderSubtle
} as const

export type ColorPalette = typeof colorPalette
export type TypographyScale = typeof typography
export type SpacingScale = typeof spacing
export type RadiiScale = typeof radii
export type Shadows = typeof shadows
export type ComponentTokens = typeof componentTokens

export const theme = {
  colorPalette,
  typography,
  spacing,
  radii,
  shadows,
  transitions,
  layout,
  componentTokens,
  elevation
}

export type ThemeDefinition = typeof theme

export default theme
