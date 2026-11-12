import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    strictPort: true,
    // 本地开发使用同源请求，由 Vite 转发至 FastAPI。
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
