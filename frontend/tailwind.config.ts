import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#20201d",
        paper: "#f6f4ef",
        line: "#ded9cf",
        skill: "#138a63",
        job: "#2f68b2",
        company: "#b7791f"
      }
    }
  },
  plugins: []
};

export default config;
