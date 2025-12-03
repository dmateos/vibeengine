import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Listen on all network interfaces
    port: 5173,
    allowedHosts: [
      'dev0.lan.mateos.cc',
      'home.mateos.cc',
      'localhost',
      '.lan.mateos.cc', // Allow all subdomains of lan.mateos.cc
      '.mateos.cc', // Allow all subdomains of mateos.cc
    ],
  },
})
