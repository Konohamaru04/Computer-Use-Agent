/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1f2520",
        panel: "#f6f5ef",
        line: "#d9d6c8",
        moss: "#2f6f4e",
        amber: "#b86f24",
      },
      boxShadow: {
        soft: "0 10px 30px rgba(31, 37, 32, 0.08)",
      },
    },
  },
  plugins: [],
};
