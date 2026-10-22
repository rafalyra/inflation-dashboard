import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    // Threads start faster and use less memory than forked processes.
    pool: 'threads',
  },
});
