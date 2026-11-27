import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: "#080a12",
          panel: "#121420",
          elevated: "#1b1d2d",
        },
        accent: {
          DEFAULT: "#8b7cf6",
          blue: "#6574e9",
        },
        border: {
          DEFAULT: "#262941",
        },
      },
      borderRadius: {
        xl2: "1rem",
      },
    },
  },
  plugins: [],
};
export default config;
