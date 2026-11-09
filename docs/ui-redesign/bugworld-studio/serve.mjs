// No dependencies; loopback only. Serve the prototype and an explicit asset allowlist.
import http from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../../..');
const mime = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.json':'application/json; charset=utf-8'};
const pages = new Set(['index.html','studio.css','studio.js','tokens.css','manifest.json']);
const species = ['butterfly','beetle','ladybug','caterpillar'];
const assets = new Map();
for (const s of species) {
  for (const kind of ['lines','mask']) assets.set(`/assets/${s}-${kind}.png`,path.join(root,`app/src/main/assets/v3/templates/${s}-${kind}.png`));
  assets.set(`/assets/${s}.svg`,path.join(root,`assets-src/v3-review/lineart/icons/${s}.svg`));
}
for (const icon of ['crayon','fill','eraser','undo','redo','save','preview','leaf','close','album']) {
  assets.set(`/assets/${icon}.svg`,path.join(root,`assets-src/v3-review/ui/icons/${icon}.svg`));
}
assets.set('/assets/logo.svg',path.join(root,'assets-src/v3-review/ui/brand/bugworld-logo.svg'));
const server = http.createServer(async (req,res) => {
  try {
    const route = new URL(req.url, 'http://localhost').pathname;
    const page = route === '/' ? 'index.html' : route.slice(1);
    const file = assets.get(route) || (pages.has(page) ? path.join(here,page) : null);
    if (!file || req.method !== 'GET') { res.writeHead(404); res.end('Not found'); return; }
    const data = await readFile(file);
    res.writeHead(200,{'Content-Type':mime[path.extname(file)] || 'application/octet-stream','Cache-Control':'no-cache','X-Content-Type-Options':'nosniff'});res.end(data);
  } catch { res.writeHead(500);res.end('Prototype asset unavailable'); }
});
server.listen(4178,'127.0.0.1',()=>console.log('BugWorld design prototype: http://127.0.0.1:4178'));
