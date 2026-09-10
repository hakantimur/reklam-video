/**
 * Local Ad Director — Tailwind tema token'ları.
 * Renk paleti docs/IMPLEMENTATION_SPEC_TR.md §5.1'den birebir alınmıştır.
 * Bu değerler dışında rastgele marka rengi eklenmez.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0B1020",
        surface: "#151D31",
        accent: "#7C6CFF",
        success: "#35CBA4",
        warning: "#F6C76A",
        error: "#F27777",
      },
    },
  },
  plugins: [],
};
