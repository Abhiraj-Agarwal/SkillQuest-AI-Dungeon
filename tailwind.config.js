/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,jsx}',
    './components/**/*.{js,jsx}',
    './app/combat/*/*.{js,jsx}',
    './app/boss/*/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        void: '#0c0a14',
        stone: {
          DEFAULT: '#2a2438',
          dark: '#1a1523',
          light: '#3d3450',
        },
        ember: {
          DEFAULT: '#ff6b3d',
          dim: '#b8492a',
        },
        arcane: {
          DEFAULT: '#6ee7d0',
          dim: '#3a8c7c',
        },
        gold: {
          DEFAULT: '#e8b339',
          dim: '#a87f22',
        },
        parchment: {
          DEFAULT: '#ece3cf',
          dim: '#a89f8c',
        },
        blood: '#c43d3d',
      },
      fontFamily: {
        display: ['"Press Start 2P"', 'cursive'],
        body: ['"VT323"', 'monospace'],
      },
      boxShadow: {
        'pixel': '4px 4px 0 0 #000',
        'pixel-sm': '2px 2px 0 0 #000',
        'pixel-lg': '6px 6px 0 0 #000',
        'pixel-arcane': '0 0 0 2px #6ee7d0, 4px 4px 0 0 #000',
        'pixel-ember': '0 0 0 2px #ff6b3d, 4px 4px 0 0 #000',
      },
      keyframes: {
        shake: {
          '0%, 100%': { transform: 'translateX(0)' },
          '20%': { transform: 'translateX(-4px)' },
          '40%': { transform: 'translateX(4px)' },
          '60%': { transform: 'translateX(-3px)' },
          '80%': { transform: 'translateX(3px)' },
        },
        flicker: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.85 },
        },
        floatUp: {
          '0%': { transform: 'translateY(0)', opacity: 1 },
          '100%': { transform: 'translateY(-40px)', opacity: 0 },
        },
      },
      animation: {
        shake: 'shake 0.4s ease-in-out',
        flicker: 'flicker 2s ease-in-out infinite',
        floatUp: 'floatUp 1s ease-out forwards',
      },
    },
  },
  plugins: [],
};
