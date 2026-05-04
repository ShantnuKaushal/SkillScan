import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#25221f",
        paper: "#f4f2ed",
        line: "#d7d1c7",
        skill: "#a24b2a",
        job: "#4d4a43",
        company: "#6f5a3d",
        selected: "#0f766e"
      }
    }
  },
  plugins: []
};

export default config;
