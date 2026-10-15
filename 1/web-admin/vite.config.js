import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  cacheDir: 'node_modules/.vite-cache',
  root: '.',
  configFile: './vite.config.js',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    // 忽略编辑器/工具写入时产生的临时目录（如 .xxx.vue.1234.abcd.tmpdir）
    // 否则 Vite 的 FSWatcher 会尝试 watch 这些瞬时目录并抛
    //   EBUSY: resource busy or locked, watch '...tmpdir/xxx.tmp'
    // 导致 dev server 直接退出（本项目已复现两次，2026-10-03 由 DSH 修复）
    watch: {
      ignored: [
        '**/.*.tmpdir/**',
        '**/*.tmpdir/**',
        '**/.*.tmp',
        '**/*.tmp',
        '**/.DS_Store'
      ]
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true
      },
      '/uploads': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true
      }
    }
  }
})