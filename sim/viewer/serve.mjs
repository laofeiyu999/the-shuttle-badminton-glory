// 静态服务：http://127.0.0.1:5180 ；同时把 ../out 映射到 /out
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path'; import url from 'node:url';
const here = path.dirname(url.fileURLToPath(import.meta.url));
const types = { '.html':'text/html; charset=utf-8', '.js':'text/javascript', '.mjs':'text/javascript', '.json':'application/json', '.css':'text/css', '.glb':'model/gltf-binary' };
http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]); if (p === '/') p = '/index.html';
  const file = p.startsWith('/out/') ? path.join(here, '..', p) : path.join(here, p);
  fs.readFile(file, (e, d) => { if (e) { res.writeHead(404); res.end('404'); return; }
    res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' }); res.end(d); });
}).listen(5180, '127.0.0.1', () => console.log('仿真查看器：http://127.0.0.1:5180'));
