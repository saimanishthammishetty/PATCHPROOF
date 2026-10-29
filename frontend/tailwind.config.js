/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#090812',
        'background-secondary': '#100E20',
        surface: '#17142A',
        'surface-elevated': '#201B38',
        'brand-violet': '#8B5CF6',
        'brand-cyan': '#22D3EE',
        'text-primary': '#F4F1FF',
        'text-secondary': '#A6A0BD',
        'severity-critical': '#F43F5E',
        'severity-high': '#FB923C',
        'severity-medium': '#FACC15',
        'severity-low': '#34D399',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
