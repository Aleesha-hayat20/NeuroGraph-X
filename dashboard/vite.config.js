import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The dashboard talks to the FastAPI server only through /api (memo 0012).
// The proxy forwards /api/... to the server and removes the /api prefix, so the API
// needs no CORS setting. The same rule applies to `npm run dev` and `npm run preview`.
const api = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: { proxy: api },
  preview: { proxy: api },
})
