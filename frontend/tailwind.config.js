/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: '#150F26',
          50: '#F6F4FB',
          100: '#E9E4F5',
          400: '#5F5480',
          600: '#292936',
          800: '#1D1D28',
          900: '#14141C',
        },
        brand: {
          DEFAULT: '#00ABBC',
          50: '#F0FAFB',
          100: '#D9F2F4',
          200: '#AEE1E6',
          400: '#3FC4CE',
          500: '#00ABBC',
          600: '#008996',
          700: '#006771',
        },
        // Mapped violet to the new teal palette so old classes turn teal
        violet: {
          DEFAULT: '#00ABBC',
          400: '#3FC4CE',
          500: '#00ABBC',
          600: '#008996',
        },
        cloud: {
          DEFAULT: '#FAF9FE',
          100: '#FFFFFF',
          200: '#F3EFFB',
        },
        // Mapped spark to the new teal color
        spark: {
          DEFAULT: '#00ABBC',
          500: '#00ABBC',
        },
      },
      fontFamily: {
        display: ['"Sora"', 'sans-serif'],
        body: ['"Inter"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      backgroundImage: {
        // Gradients updated to use only variations of #00ABBC (Light teal to Base teal to Dark teal)
        'brand-gradient': 'linear-gradient(135deg, #3FC4CE 0%, #00ABBC 100%)',
        'brand-gradient-soft': 'linear-gradient(135deg, rgba(0,171,188,0.05) 0%, rgba(0,171,188,0.15) 100%)',
        'vivid-gradient': 'linear-gradient(120deg, #3FC4CE 0%, #00ABBC 55%, #006771 100%)',
        'ink-gradient': 'linear-gradient(180deg, #150F26 0%, #1E1638 100%)',
      },
      boxShadow: {
        glass: '0 8px 32px 0 rgba(0, 171, 188, 0.14)',
        'glass-lg': '0 20px 60px -10px rgba(21, 15, 38, 0.28)',
        card: '0 2px 8px rgba(21, 15, 38, 0.06), 0 12px 24px -8px rgba(21, 15, 38, 0.08)',
      },
      borderRadius: {
        xl2: '1.25rem',
        '3xl': '1.75rem',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-12px)' },
        },
        'fade-up': {
          '0%': { opacity: 0, transform: 'translateY(24px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-500px 0' },
          '100%': { backgroundPosition: '500px 0' },
        },
      },
      animation: {
        float: 'float 6s ease-in-out infinite',
        'fade-up': 'fade-up 0.6s ease-out forwards',
        shimmer: 'shimmer 1.6s linear infinite',
      },
    },
  },
  plugins: [],
}