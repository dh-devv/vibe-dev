/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icons/icon.svg", "samples.json"],
      manifest: {
        name: "미루기 재판소",
        short_name: "미루기 재판소",
        description: "미루는 이유를 AI 공방으로 드러내고 맞춤 처방을 판결받는 앱",
        lang: "ko",
        start_url: "/",
        scope: "/",
        display: "standalone",
        orientation: "portrait",
        background_color: "#1d120a",
        theme_color: "#3b2314",
        icons: [
          { src: "icons/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
          { src: "icons/icon-maskable.svg", sizes: "any", type: "image/svg+xml", purpose: "maskable" }
        ]
      },
      workbox: {
        // API와 인증 경로, 사용자별 응답은 캐시하지 않는다.
        navigateFallbackDenylist: [/^\/api\//, /^\/auth\//],
        runtimeCaching: []
      }
    })
  ],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/auth": "http://localhost:8000"
    }
  },
  test: { environment: "node", include: ["tests/**/*.test.ts"] }
});
