/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Deep charcoal / graphite enterprise palette
        background: '#111315',
        'background-secondary': '#16191D',
        surface: '#1B1E21',
        'surface-elevated': '#24282D',
        'surface-border': '#30363B',
        'border-subtle': '#262A2E',

        // Brand & Accents (Muted Emerald & Warm Amber)
        'accent-emerald': '#35A477',
        'accent-emerald-hover': '#2D8A64',
        'accent-emerald-muted': 'rgba(53, 164, 119, 0.12)',
        'accent-amber': '#D6A24A',
        'accent-amber-hover': '#BF8F3D',
        'accent-amber-muted': 'rgba(214, 162, 74, 0.12)',

        // Typography
        'text-primary': '#E8EAED',
        'text-secondary': '#92999F',
        'text-muted': '#656C73',
        // Security Severities
        'severity-critical': '#E05252',
        'severity-high': '#D6A24A',
        'severity-medium': '#C7A843',
        'severity-low': '#35A477',

        // Legacy compatibility mappings to prevent any missing classes
        'brand-violet': '#35A477',
        'brand-cyan': '#35A477',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      borderRadius: {
        'card': '8px',
        'panel': '6px',
      }
    },
  },
  plugins: [],
}

