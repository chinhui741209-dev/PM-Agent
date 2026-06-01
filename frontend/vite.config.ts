import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // 把 /api 代理到後端，前端程式碼用相對路徑即可
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
