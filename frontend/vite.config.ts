import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@app": fileURLToPath(new URL("./src/app", import.meta.url)),
      "@api": fileURLToPath(new URL("./src/api", import.meta.url)),
      "@features": fileURLToPath(new URL("./src/features", import.meta.url)),
      "@shared": fileURLToPath(new URL("./src/shared", import.meta.url)),
      "@chat": fileURLToPath(new URL("./src/shared/ui/chat/index.ts", import.meta.url)),
    },
  },
  server: { host: "127.0.0.1", proxy: { "/api": { target: "http://127.0.0.1:8000" } } },
});
