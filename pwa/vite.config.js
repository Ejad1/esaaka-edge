import { defineConfig } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  base: './',
  build: { target: 'es2022', chunkSizeWarningLimit: 1500 },
  plugins: [
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        globPatterns: ['**/*.{js,mjs,css,html,wasm,onnx,json,svg,png,ico,webmanifest}'],
        maximumFileSizeToCacheInBytes: 40 * 1024 * 1024,
        globIgnores: ['assets/ort-wasm-*.wasm'],   // the runtime is served from /ort/ (single copy)
        navigateFallback: 'index.html',
      },
      manifest: {
        name: 'Esaaka Edge',
        short_name: 'Esaaka Edge',
        description: 'Offline coffee-leaf triage that tells you when it is not sure.',
        start_url: './',
        scope: './',
        display: 'standalone',
        background_color: '#0f2a1a',
        theme_color: '#1b6e3f',
        icons: [
          { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
    }),
  ],
});
