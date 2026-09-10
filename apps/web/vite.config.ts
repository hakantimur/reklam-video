import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Local Ad Director — Vite yapılandırması.
// Bkz. docs/IMPLEMENTATION_SPEC_TR.md §6.1. Backend ayrı süreçte
// 127.0.0.1:8765 üzerinde çalışır; bu UI ondan bağımsız bir portta
// (varsayılan 5173) sunulur. API istekleri apps/web/src/api/client.ts
// içinde mutlak backend adresine gider (bkz. o dosyadaki not).
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: false,
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
