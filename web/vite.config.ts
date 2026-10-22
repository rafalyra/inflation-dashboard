import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// VITE_ROUTER=memory builds a self-contained preview (relative asset paths, in-memory
// routes) that works from any sub-path. The default build uses normal paths.
const preview = process.env.VITE_ROUTER === 'memory';

export default defineConfig({
  base: preview ? './' : '/',
  plugins: [react()],
  test: {
    environment: 'jsdom',
    // Threads start faster and use less memory than forked processes.
    pool: 'threads',
  },
});
