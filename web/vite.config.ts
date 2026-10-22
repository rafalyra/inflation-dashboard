import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// VITE_ROUTER=hash builds a self-contained preview (relative asset paths, #/ routes) that
// works when served from any sub-path. The default build uses normal paths.
const hashPreview = process.env.VITE_ROUTER === 'hash';

export default defineConfig({
  base: hashPreview ? './' : '/',
  plugins: [react()],
  test: {
    environment: 'jsdom',
    // Threads start faster and use less memory than forked processes.
    pool: 'threads',
  },
});
