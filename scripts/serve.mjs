/* Server statico per `ui/`, zero dipendenze.
 *
 * Serve un server e non `file://` perche' i moduli ES sotto file:// sono
 * bloccati dalla CORS. Serve un server MINIMO e non Vite perche' Vite non e'
 * in SPEC §4 e il CLAUDE.md vieta di aggiungere dipendenze non elencate.
 * La porta 5173 e' quella indicata in §11.7.
 */

import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const RADICE = resolve(fileURLToPath(new URL("../ui", import.meta.url)));
export const PORTA = 5173;

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".woff2": "font/woff2",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

export function creaServer() {
  return createServer(async (req, res) => {
    const rel = normalize(decodeURIComponent(new URL(req.url, "http://x").pathname));
    const percorso = join(RADICE, rel);

    // Traversal: dopo normalize(), il percorso deve stare sotto la radice.
    // Stesso principio di SPEC §6.1 — il controllo va DOPO la risoluzione.
    if (percorso !== RADICE && !percorso.startsWith(RADICE + sep)) {
      res.writeHead(403).end("fuori radice");
      return;
    }
    try {
      const corpo = await readFile(percorso);
      res.writeHead(200, { "content-type": MIME[extname(percorso)] ?? "application/octet-stream" });
      res.end(corpo);
    } catch {
      res.writeHead(404).end("non trovato");
    }
  });
}

export function avvia(porta = PORTA) {
  return new Promise((ok) => {
    const s = creaServer();
    s.listen(porta, "127.0.0.1", () => ok(s));
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  await avvia();
  console.log(`galleria su http://127.0.0.1:${PORTA}/gallery.html`);
}
