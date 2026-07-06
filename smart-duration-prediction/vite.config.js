import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api/dify': {
        target: 'http://172.16.204.124',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/dify/, '/v1'),
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('Authorization', 'Bearer app-eqYhrSTYq86vbBXnAAuMQM15')
          })
        }
      },
      '/api/daily': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/api/auth': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/api/admin': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/api/planning': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
