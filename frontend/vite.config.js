import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/topics': 'http://127.0.0.1:8000',
      '/discussions': 'http://127.0.0.1:8000',
      '/analytics': 'http://127.0.0.1:8000',
      '/docs': 'http://127.0.0.1:8000',
      '/openapi.json': 'http://127.0.0.1:8000',
    },
  },
});
