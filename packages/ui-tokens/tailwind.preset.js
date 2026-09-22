/**
 * @autoforce/ui-tokens — Tailwind preset
 * 颜色经 CSS 变量引用，支持 `bg-accent/10` 等透明度修饰。
 * 需在页面中引入 tokens.css（变量定义）。
 */

const ch = (name) => `rgb(var(--ui-${name}) / <alpha-value>)`;

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [],
  theme: {
    extend: {
      colors: {
        bg: ch('bg'),
        surface: ch('surface'),
        'surface-2': ch('surface-2'),
        text: {
          DEFAULT: ch('text'),
          secondary: ch('text-secondary'),
          tertiary: ch('text-tertiary'),
        },
        accent: {
          DEFAULT: ch('accent'),
          hover: ch('accent-hover'),
        },
        'on-accent': ch('on-accent'),
        separator: `rgb(var(--ui-separator) / var(--ui-separator-alpha))`,
        success: ch('success'),
        warning: ch('warning'),
        danger: ch('danger'),
      },
      fontFamily: {
        sans: ['var(--ui-font-sans)'],
      },
      borderRadius: {
        sm: 'var(--ui-radius-sm)',
        md: 'var(--ui-radius-md)',
        lg: 'var(--ui-radius-lg)',
        xl: 'var(--ui-radius-xl)',
        '2xl': 'var(--ui-radius-2xl)',
        pill: 'var(--ui-radius-pill)',
      },
      boxShadow: {
        card: 'var(--ui-shadow-card)',
        popover: 'var(--ui-shadow-popover)',
        modal: 'var(--ui-shadow-modal)',
      },
      transitionDuration: {
        fast: 'var(--ui-duration-fast)',
        base: 'var(--ui-duration-base)',
        slow: 'var(--ui-duration-slow)',
      },
      transitionTimingFunction: {
        apple: 'var(--ui-ease)',
      },
    },
  },
  plugins: [],
};
