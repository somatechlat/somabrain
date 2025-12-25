import { defineConfig } from 'vite'

export default defineConfig({
    root: '.',
    base: '/',
    server: {
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://localhost:9696',
                changeOrigin: true,
            },
        },
    },
    build: {
        outDir: 'dist',
        emptyOutDir: true,
    },
})
