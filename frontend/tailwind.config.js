/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#dce8ff",
          500: "#3b6fed",
          600: "#2d57c9",
          700: "#24449e",
        },
      },
    },
  },
  plugins: [],
};
