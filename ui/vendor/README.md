# Librerie di terze parti

Copiate da `node_modules` con `npm run vendor` — vedi `scripts/vendor.mjs`.
Non modificarle a mano: la prossima esecuzione le sovrascrive.

| File | Pacchetto | Licenza |
|---|---|---|
| `augmented-ui.min.css` | augmented-ui | BSD-2-Clause 2.0.0 |
| `uPlot.min.css`<br>`uPlot.esm.js` | uplot | MIT 1.6.32 |
| `winbox.bundle.min.js` | winbox | Apache-2.0 0.2.82 |
| `three/three.module.js`<br>`three/three.core.js`<br>`three/addons/lines/Line2.js`<br>`three/addons/lines/LineGeometry.js`<br>`three/addons/lines/LineMaterial.js`<br>`three/addons/lines/LineSegments2.js`<br>`three/addons/lines/LineSegmentsGeometry.js` | three | MIT 0.185.1 |
| `anime.esm.min.js` | animejs | MIT 4.5.0 |
| `three-mesh-bvh/index.module.js` | three-mesh-bvh | MIT 0.9.14 |
| `pixi.min.mjs`<br>`pixi-unsafe-eval/init.mjs`<br>`pixi-unsafe-eval/particle/generateParticleUpdatePolyfill.mjs`<br>`pixi-unsafe-eval/particle/particleUpdateFunctions.mjs`<br>`pixi-unsafe-eval/shader/generateShaderSyncPolyfill.mjs`<br>`pixi-unsafe-eval/ubo/generateUboSyncPolyfill.mjs`<br>`pixi-unsafe-eval/ubo/uboSyncFunctions.mjs`<br>`pixi-unsafe-eval/uniforms/generateUniformsSyncPolyfill.mjs`<br>`pixi-unsafe-eval/uniforms/uniformSyncFunctions.mjs` | pixi.js | MIT 8.19.0 |
| `d3-shape/arc.js`<br>`d3-shape/constant.js`<br>`d3-shape/math.js`<br>`d3-shape/path.js` | d3-shape | ISC 3.2.0 |
| `d3-path/index.js`<br>`d3-path/path.js` | d3-path | ISC 3.1.0 |

Gli specificatori nudi (`three`, `d3-path`) li risolve l'import map in
`ui/gallery.html` e `ui/index.html`. Aggiungendo una libreria qui, la voce
va aggiunta anche li'.

Sono esenti dall'audit del SORGENTE (livello 2): i letterali dentro una
libreria di terzi non sono nostri da correggere, e la scelta di usarla e'
gia' stata fatta in SPEC §11.3. **Restano soggette all'audit del valore
calcolato (livello 1)** su ogni elemento che finisce nei nostri componenti:
se uPlot dipinge un asse con un colore fuori palette, l'audit lo vede.
