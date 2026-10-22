// Build a single-page preview for hosts that only allow inline scripts and styles:
// JS, CSS and fonts are inlined into one HTML file; the data JSON stays alongside it.
//   node scripts/build-preview.mjs <outDir>
import { execSync } from 'node:child_process';
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

const out = process.argv[2] ?? 'dist-preview';
const build = 'dist-preview-build';
rmSync(build, { recursive: true, force: true });
execSync(`npx vite build --outDir ${build}`, { stdio: 'inherit', env: { ...process.env, VITE_ROUTER: 'memory' } });

const html = readFileSync(join(build, 'index.html'), 'utf8');
const read = (rel) => readFileSync(join(build, rel.replace(/^\.\//, '')));

function inlineCss(rel) {
  const css = read(rel).toString('utf8');
  // Fonts referenced by the stylesheet become data: URIs.
  return css.replace(/url\((\.\/)?([^)'"]+\.(woff2?|ttf))\)/g, (_, __, file) => {
    const path = join(dirname(rel.replace(/^\.\//, '')), file);
    const type = file.endsWith('.woff2') ? 'font/woff2' : file.endsWith('.woff') ? 'font/woff' : 'font/ttf';
    return `url(data:${type};base64,${readFileSync(join(build, path)).toString('base64')})`;
  });
}

const title = html.match(/<title>.*?<\/title>/s)?.[0] ?? '';
const styles = [...html.matchAll(/<link rel="stylesheet"[^>]*href="([^"]+)"[^>]*>/g)].map((m) => `<style>${inlineCss(m[1])}</style>`);
const scripts = [...html.matchAll(/<script type="module"[^>]*src="([^"]+)"[^>]*><\/script>/g)].map(
  (m) => `<script type="module">${read(m[1]).toString('utf8').replaceAll('</script', '<\/script')}</script>`,
);
const page = ['<meta charset="utf-8">', title, ...styles, '<div id="root"></div>', ...scripts].join('\n');

rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });
writeFileSync(join(out, 'index.html'), page);
cpSync(join(build, 'data'), join(out, 'data'), { recursive: true });
rmSync(build, { recursive: true, force: true });
console.log(`preview written to ${out} (${(page.length / 1024 / 1024).toFixed(2)} MB)`);
