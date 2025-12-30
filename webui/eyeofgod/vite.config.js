import { defineConfig } from 'vite'

export default defineConfig({
    root: '.',
    base: '/',
    server: {
        port: 30173,
        proxy: {
            '/api': {
                target: 'http://localhost:9696',
                changeOrigin: true,
            },
        },
        fs: {
            allow: ['..'], // Allow serving files from parent directories (design-system)
        },
    },
    build: {
        outDir: 'dist',
        emptyOutDir: true,
    },
})
