import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, /api is proxied to the FastAPI server so there are no CORS issues.
// In production set VITE_API_URL to your backend URL (see README).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://localhost:8000' }
  }
})
