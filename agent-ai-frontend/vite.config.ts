import { resolve } from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": resolve(import.meta.dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/auth": "http://127.0.0.1:8000",
      "/channels": "http://127.0.0.1:8000",
      "/knowledge-blocks": "http://127.0.0.1:8000",
      "/prompts": "http://127.0.0.1:8000",
      "/connectors": "http://127.0.0.1:8000",
      "/evaluation": "http://127.0.0.1:8000",
    },
  },
})
