// Servidor de produção do frontend para plataformas sem reescrita de rotas (ex.: Vertra Cloud).
// Serve o build do Vite em ./dist e devolve index.html para as rotas do React Router.
// Sem dependências: só módulos nativos do Node.
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, join, normalize, resolve, sep } from 'node:path';

const root = resolve('dist');
const port = Number(process.env.PORT || 80);
const apiOrigin = (() => {
  try { return new URL(process.env.API_BASE_URL || '').origin; } catch { return ''; }
})();

const types = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.webp': 'image/webp', '.ico': 'image/x-icon', '.ttf': 'font/ttf', '.woff': 'font/woff', '.woff2': 'font/woff2', '.txt': 'text/plain; charset=utf-8',
};

// Mesma política do Caddyfile de produção, mais as fontes do Google usadas no index.css.
const csp = [
  "default-src 'self'", "script-src 'self'", "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com", "img-src 'self' data: blob:", `connect-src 'self' ${apiOrigin}`.trim(),
  "frame-src 'self' about:", "object-src 'none'", "base-uri 'self'", "form-action 'self'", "frame-ancestors 'none'",
].join('; ');

const baseHeaders = {
  'Content-Security-Policy': csp, 'Strict-Transport-Security': 'max-age=31536000', 'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer', 'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
};

async function fileFor(urlPath) {
  const decoded = decodeURIComponent(urlPath.split('?')[0]);
  const candidate = resolve(join(root, normalize(decoded)));
  if (candidate !== root && !candidate.startsWith(root + sep)) return null;
  try { return (await stat(candidate)).isFile() ? candidate : null; } catch { return null; }
}

createServer(async (req, res) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.writeHead(405, { ...baseHeaders, Allow: 'GET, HEAD' }).end();
    return;
  }
  try {
    let path = await fileFor(req.url || '/');
    // Rota do React Router (sem extensão): devolve o app. Arquivo inexistente com extensão: 404.
    if (!path && !extname((req.url || '/').split('?')[0])) path = join(root, 'index.html');
    if (!path) { res.writeHead(404, baseHeaders).end('Não encontrado'); return; }
    const body = await readFile(path);
    const cache = path.includes(`${sep}assets${sep}`) ? 'public, max-age=31536000, immutable' : 'no-cache';
    res.writeHead(200, { ...baseHeaders, 'Content-Type': types[extname(path)] || 'application/octet-stream', 'Cache-Control': cache });
    res.end(req.method === 'HEAD' ? undefined : body);
  } catch {
    res.writeHead(500, baseHeaders).end('Erro interno');
  }
}).listen(port, '0.0.0.0', () => console.log(`Dash web na porta ${port}`));
