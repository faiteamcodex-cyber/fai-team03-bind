import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { loadEnv } from 'vite'
import { defineConfig } from 'vitest/config'

// BIND frontend — Member 4
// Vite + React 18 + TypeScript (strict) + TailwindCSS v4 + Zustand + MapLibre GL
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  /**
   * Extra hostnames the dev server may be reached through (container preview,
   * LAN IP via ngrok, a teammate's tunnel...). Comma-separated.
   * Example: VITE_ALLOWED_HOSTS=".e2b.app,192.168.1.20"
   * Vite already allows localhost and the machine's own IPs.
   */
  const extraAllowedHosts = String(env.VITE_ALLOWED_HOSTS ?? '')
    .split(',')
    .map((host) => host.trim())
    .filter(Boolean)

  return {
    plugins: [react(), tailwindcss()],

    resolve: {
      alias: {
        // Keep in sync with `paths` in tsconfig.app.json
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },

    server: {
      // `host: true` binds 0.0.0.0 so the dev server is reachable from a
      // container or another machine on the LAN.
      host: true,
      port: Number(env.VITE_DEV_PORT ?? 5173),
      strictPort: true,
      ...(extraAllowedHosts.length > 0 ? { allowedHosts: extraAllowedHosts } : {}),
    },

    preview: {
      host: true,
      port: 4173,
      strictPort: true,
      ...(extraAllowedHosts.length > 0 ? { allowedHosts: extraAllowedHosts } : {}),
    },

    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      include: ['src/**/*.{test,spec}.{ts,tsx}'],
      // MapLibre needs canvas/WebGL; component tests that mount a real map get
      // an explicit stub in src/test/setup.ts when we reach that step.
      css: false,
    },
  }
})
