import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Django dev server (ดู README) — ส่ง /api, /admin, /static ต่อไปที่ Django
// ทำให้ React กับ API อยู่ origin เดียวกัน ไม่ต้องตั้ง CORS และใช้ session cookie ได้ตรง ๆ
const DJANGO = process.env.DJANGO_URL ?? 'http://127.0.0.1:8003'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': DJANGO,
      '/admin': DJANGO,
      '/static': DJANGO,
    },
  },
  build: {
    // ApexCharts ใหญ่ ~1 MB แยกเป็น chunk ของหน้า dashboard แล้ว
    chunkSizeWarningLimit: 1100,
  },
})
