/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#F6F5ED",
        surface: "#FFFFFF",
        "surface-low": "#ECF6ED",
        "surface-muted": "#E6F1E7",
        border: "#E5E9E5",
        foreground: "#202923",
        muted: "#68736C",
        primary: "#003421",
        "primary-container": "#174B35",
        "primary-soft": "#B8EFD0",
        secondary: "#156C43",
        "secondary-container": "#A2F4C0",
        tertiary: "#163219",
        accent: "#A8C9A5",
        warning: "#C2410C",
        danger: "#BA1A1A",
        success: "#156C43",
      },
      fontFamily: {
        heading: ['"Plus Jakarta Sans"', "system-ui", "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.5rem",
        "3xl": "2rem",
      },
      boxShadow: {
        card: "0 1px 3px 0 rgba(32, 41, 35, 0.04)",
        raised: "0 4px 12px -2px rgba(23, 75, 53, 0.08)",
        float: "0 12px 28px -6px rgba(23, 75, 53, 0.16)",
      },
    },
  },
  plugins: [],
};
