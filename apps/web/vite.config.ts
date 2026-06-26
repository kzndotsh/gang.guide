import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { execSync } from 'node:child_process';
import { defineConfig } from 'vite';

const gitVersion = execSync('git describe --tags --always 2>/dev/null || echo dev').toString().trim();

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  define: { __APP_VERSION__: JSON.stringify(gitVersion) },
});
