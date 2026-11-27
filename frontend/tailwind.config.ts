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
          DEFAULT: "#0b0f14",
          panel: "#11161d",
          elevated: "#161c25",
        },
        accent: {
          DEFAULT: "#22d3ee",
          blue: "#3b82f6",
        },
        border: {
          DEFAULT: "#232b36",
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
