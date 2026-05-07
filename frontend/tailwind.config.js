/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'sauce-dark': '#1e293b',
        'sauce-green': '#10b981',
      }
    },
  },
  plugins: [],
}