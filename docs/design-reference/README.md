# Riferimenti visivi — JARVIS OS

Leggere questo file **prima** di ogni componente visivo.

I riferimenti si dividono in **due famiglie**, e la distinzione e' la cosa piu'
importante di questo documento.

---

## famiglia-a/ — DA SEGUIRE

Information design cinematografico.

| Caratteristica | Osservazione |
|---|---|
| Fondo | blu-nero quasi puro, mai grigio |
| Luminosita' | dal **contrasto** contro il nero, **mai da bloom o glow** |
| Densita' | estrema. Lo spazio vuoto e' raro e sempre intenzionale |
| Tipografia | condensata per i titoli, **monospace per ogni numero** |
| Bordi | hairline, mai spessi |
| Accento caldo | rosso-arancio, **~10% della superficie**, sempre semantico |
| Contenuto | dati veri, pagine web vere, video veri incassati |
| Etichette | `ver 12`, `A02`, `QUERY COMPLETE`, coordinate, hex |

### I file e a cosa servono

| File | Cosa insegna | Usato per |
|---|---|---|
| `01-desktop-mcu-completo.png` | griglia di pannelli, densita', dock, barra | layout generale, §13 |
| `02-oggetti-3d-wireframe-in-pannelli.png` | **chiave per il 3D**: primitive wireframe con linee di costruzione, isolate in pannelli etichettati `ver 1..10`, densita' linee variabile con la curvatura | §11.10 ParametricComponent |
| `03-database-tabellare-denso.png` | densita' tabellare, righe evidenziate, monospace | file manager, pannelli dati |
| `04-analisi-armatura-grafo-nodi.png` | **grafo a nodi** con linee ortogonali e raccordi | mesh agenti, §13 |
| `05-dashboard-news.png` | player incassato, lista storie, mappa con archi, ticker rosso | pannello news, §15 |
| `06-access-server-trace-archive.png` | nuvola di punti sferica, radiale, grande numerale d'angolo | §17.4 point cloud |
| `07-griglia-9up-con-web-incassato.png` | **chiave webview**: pagine web reali dentro i pannelli (barra URL visibile) | §6.3 |
| `08-archivio-piani-stratificati.png` | **chiave CSS 3D**: documenti su piani Z traslucidi, filmstrip di miniature | §11.4 — NON three.js |
| `09-board-investigativa-3d.png` | **chiave CSS 3D**: carte a profondita' e angoli diversi, chip-etichetta rossi | §11.4 — NON three.js |
| `10-globo-gps-locator.png` | globo con archi, chrome piatto attorno, equalizzatore vocale | three-globe + d3-geo |
| `11-tavola-periodica-scanner.png` | tavola periodica (= CSS Grid), quadranti radiali, header rosso | §11.5 |
| `12-logo-anelli-concentrici.png` | anelli disallineati, tick, centri sfalsati | §11.10 ReactorRing |

---

## famiglia-b/ — NON SEGUIRE

Asset motion-graphics da stock. Hanno **bloom, alone, saturazione**, e i loro
quadranti non mostrano nulla di vero. Contraddicono frontalmente la famiglia A
e il pilastro "nessun glow" di `docs/SPEC.md` §10.

| File | Perche' e' escluso |
|---|---|
| `01-hud-medico-glow.png` | glow diffuso, cornici a staffa decorative |
| `02-render-stock-angolato.png` | bloom, prospettiva finta, dati inventati |
| `03-data-wall-stock.png` | alone su ogni elemento, densita' decorativa non informativa |
| `04-digital-counter-tool.png` | template After Effects, glow massiccio |

**Come usarli comunque**: se una FORMA le piace — tick, archi segmentati,
quadranti — la prenda, ma la renda **senza glow e con dati veri dentro**.
La forma si', il trattamento no.

---

## Regola per Claude Code

Quando implementi un componente visivo:

1. il prompt indica **quale file di famiglia-a** e quale riquadro
2. rendi il componente in `gallery.html?component=<nome>&tokens=audit`
3. `npx playwright screenshot ... shots/<nome>.png`
4. **LEGGI il PNG** con il tool Read
5. confrontalo con il riferimento e riporta la checklist SPEC §11.8 punto per punto
6. se un punto fallisce, **riscrivi** il componente

Il passo 4 va eseguito davvero. Uno screenshot non guardato non serve a nulla.
