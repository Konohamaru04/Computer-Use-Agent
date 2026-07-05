import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    strictPort: true,
    host: "127.0.0.1",
    port: 1420,
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(rootDir, "index.html"),
        overlay: resolve(rootDir, "overlay.html"),
        cursor: resolve(rootDir, "cursor.html"),
        cursorMarker: resolve(rootDir, "cursorMarker.html"),
      },
    },
  },
});
