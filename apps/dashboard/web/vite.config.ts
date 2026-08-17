import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base 使用相对路径，使构建产物可部署到 Cloudflare Pages 的任意域名/子路径。
export default defineConfig({
  base: './',
  plugins: [react()],
});
