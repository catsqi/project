/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        black: '#000000',
        white: '#FFFFFF',
        'neon-green': '#CCFF00'
      },
      fontFamily: {
        sans: ['Inter', 'Arial', 'sans-serif'],
      },
      boxShadow: {
        DEFAULT: 'none',   // 禁用默认阴影
        md: 'none',
        lg: 'none',
        xl: 'none',
        '2xl': 'none',
      },
      borderRadius: {
        DEFAULT: '0px',    // 禁用所有圆角
        sm: '0px',
        md: '0px',
        lg: '0px',
        xl: '0px',
        '2xl': '0px',
        '3xl': '0px',
        full: '0px',
      }
    },
  },
  plugins: [],
}
