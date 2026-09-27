import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Multi-page app: every top-level view has its own HTML document so the browser
// can deep-link (/arena, /history, /intel, /devops) without a client-side router.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        arena: resolve(__dirname, 'arena.html'),
        history: resolve(__dirname, 'history.html'),
        intel: resolve(__dirname, 'intel.html'),
        devops: resolve(__dirname, 'devops.html'),
      },
    },
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/topics': 'http://127.0.0.1:8000',
      '/discussions': 'http://127.0.0.1:8000',
      '/analytics': 'http://127.0.0.1:8000',
      '/auth': 'http://127.0.0.1:8000',
      '/profile': 'http://127.0.0.1:8000',
      '/reports': 'http://127.0.0.1:8000',
      '/docs': 'http://127.0.0.1:8000',
      '/openapi.json': 'http://127.0.0.1:8000',
    },
  },
});
