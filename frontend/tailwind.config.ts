import type { Config } from "tailwindcss";
import forms from "@tailwindcss/forms";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#18211c",
        paper: "#f5f3eb",
        moss: "#315d48",
        mist: "#dce5dd",
      },
      boxShadow: { lift: "0 12px 40px rgba(22, 40, 29, 0.08)" },
    },
  },
  plugins: [forms],
};

export default config;

