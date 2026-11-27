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
          DEFAULT: "#f3ede0",
          panel: "#fbf8f0",
          elevated: "#eae2d0",
        },
        accent: {
          DEFAULT: "#c79e4e",
          blue: "#1c4437",
        },
        border: {
          DEFAULT: "#dcd1ba",
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
