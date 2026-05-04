import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1d211f",
        paper: "#f4f7f4",
        line: "#d8e1d8",
        skill: "#0b8067",
        job: "#3d6476",
        company: "#806238"
      }
    }
  },
  plugins: []
};

export default config;
