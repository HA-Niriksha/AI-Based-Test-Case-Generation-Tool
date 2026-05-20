/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"DM Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        bg:      '#0A0C10',
        surface: '#12151C',
        card:    '#181C26',
        border:  '#252A38',
        amber:   '#FBBF24',
        amber2:  '#F59E0B',
        muted:   '#64748B',
        text:    '#E2E8F0',
        dim:     '#94A3B8',
      },
    },
  },
  plugins: [],
}
