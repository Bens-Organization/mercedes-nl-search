import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Customer JourneyAI Brand Colors
        'journey': {
          teal: '#00CE9D',      // Primary teal/cyan
          navy: '#003C5B',      // Dark navy blue
          'navy-dark': '#002840', // Darker navy for hover states
        },
      },
    },
  },
  plugins: [],
};

export default config;
