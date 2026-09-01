import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// base 使用相对路径，使构建产物可部署到 Cloudflare Workers 或其他静态域名/子路径。
export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],
  build: {
    // 模块化 ECharts 后主 chunk 约 770 KB，gzip 约 257 KB。
    // 这里保留提醒阈值，避免把可接受的图表运行时代码误判为构建失败。
    chunkSizeWarningLimit: 800,
  },
});
