# Fase 5 — esito dei criteri di accettazione

**Data**: 18 agosto 2026 · **Riferimento**: `docs/SPEC.md` §22 Fase 5
**Test**: 223 verdi (erano 218) + 133 negli eval · **Precedente**: `FASE-04.md`

---

## Il criterio di §22

> «60fps dentro il budget §10.4. Ogni componente ha parametri, versione, supera
> il gate **e il ciclo di verifica visiva**. Zero dati segnaposto.»

### 1. «60fps dentro il budget §10.4» — ✅ VERIFICATO sulla macchina vera

Misurato con i **tre motori che girano insieme** — globo (three.js), campo di
glifi (PixiJS), anelli (anime.js) — perché il budget è per frame e non per
componente: sette componenti ciascuno dentro il proprio possono sforare tutti
insieme. Banco: `ui/src/gallery/mounts/budget.js`, 300 frame per misura.

| Motore | Mediana | p95 | Tetto §10.4 | |
|---|---|---|---|---|
| three.js | **0,30 ms** | 0,50 | 8 ms | ✅ |
| PixiJS | **0,30 ms** | 0,50 | 3 ms | ✅ |
| anime.js + layout | **≈0 ms** | ≈0 | 4 ms | ✅ |
| **frame intero** | **16,70 ms** | 16,80 | 16,7 ms | ✅ **59,9 fps** |

I 16,7 ms del frame intero sono l'intervallo di vsync: il ciclo **aspetta lo
schermo**, non il contrario. Il margine è tutto quello che resta.

anime.js si misura per **differenza** — 150 frame con gli anelli fermi, 150 con
gli anelli in moto — perché gira sul proprio `requestAnimationFrame` e
cronometrarlo dall'esterno misurerebbe il nostro. La differenza è sotto il
rumore: la rotazione di cinque anelli SVG non costa niente di misurabile.

```bash
npm run bench
```

⚠️ **Il numero headless non vale, ed è diverso**: in Playwright lo stesso banco
dà **83,3 ms** per frame (12 fps), perché Chromium senza GPU rasterizza in
software con SwiftShader. È il motivo per cui il criterio si verifica in
Electron e non nel ciclo §11.7. Entrambi i numeri sono riportati apposta.

### 2. «Ogni componente ha parametri, versione, supera il gate» — ✅ VERIFICATO

Sei geometrie parametriche, tutte gatate **prima** del render, tutte con
tabella dei parametri, versione e bounding box dichiarato:

| Componente | Vertici | Note |
|---|---|---|
| `reactor-ring` | 684 | densità da `segmentsFor()`, varco progettato |
| `radial-dial` | 556 | bbox analitico da `math/arco.js`, non 2R |
| `point-cloud` | 193 | un punto per file vero del progetto |
| `globe-graticule` | 8984 | densità del parallelo dal suo raggio vero |
| `globe-terminator` | 256 | cerchio massimo dal Sole vero |
| `globe-timezones` | 312 | un punto per fuso di tzdata |

E il gate **spara** su tre guasti veri (`tests/eval_visual.py`): un fattore due
su un asse, una traslazione fuori scala, un `NaN`. Un controllo che non ha mai
bocciato nulla non è un controllo.

### 3. «…e il ciclo di verifica visiva» — ✅ ESEGUITO su sette componenti

Per ognuno: scritto → reso in galleria → screenshot → **guardato** → checklist
§11.8 → riscritto dove falliva. Le riscritture sono elencate più sotto.

### 4. «Zero dati segnaposto» — ✅ VERIFICATO, con un'assenza dichiarata

| Componente | Dato |
|---|---|
| `dials` | CPU, RAM, temperatura da psutil (topic `telemetry`) |
| `source` | i 193 file veri del progetto, con le dimensioni vere |
| `globe` | 312 fusi di `zone1970.tab` + posizione solare calcolata |
| `agents` | stato vero di router/T0/T1/T2 dal core |
| `glyphs` | i byte veri di un messaggio del canale |
| `periodic` | 118 elementi, pesi atomici IUPAC |
| `rings` | stato dell'agente dal bus |

Ogni pannello senza sorgente mostra `NESSUNA SORGENTE COLLEGATA`, non uno zero.

---

## La checklist §11.8, punto per punto

Verificata **guardando** ogni screenshot. I punti meccanici sono anche in
`tests/eval_visual.py`; i punti di giudizio — densità, percentuale dell'accento
caldo, causa dell'animazione — solo qui, perché una checklist che finge di
essere automatica su un giudizio darebbe verde a ciò che nessuno ha guardato.

| | rings | dials | source | agents | periodic | glyphs | globe |
|---|---|---|---|---|---|---|---|
| `border-radius` 0 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| taglio 45° su 1–2 vertici | ✅ 2 | ✅ 2 | ✅ 2 | ✅ 2 | ✅ 2 | ✅ 2 | ✅ 2 |
| spaziature multiple di 4 | ✅ | ✅ | ✅ | ✅ | ✅¹ | ✅ | ✅ |
| pesi hair/base/bold | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| colori dai token (audit) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| accento caldo < 10% | ✅ | ✅² | ✅ | ✅ | ✅³ | ✅ | ✅⁴ |
| tinte ≤ 3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| zero gradienti | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| zero glow/bloom/shadow | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| cinque gradini tipografici | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| numeri in mono | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| caps con letter-spacing ≥ .10em | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| dati veri | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| etichetta + ID/ver + piede | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| almeno un numero mono | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| densità vs riferimento | ✅⁵ | ✅ | ✅⁵ | ✅ | ✅ | ✅ | ✅ |
| animazione con causa | ✅⁶ | ✅⁷ | — | — | — | ✅⁸ | — |
| zero animazione ambientale | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| solo anime.js | ✅ | ✅ | — | — | — | — | — |
| testo nel DOM | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️⁹ | ✅ |
| linee 3D con `Line2` | — | — | ✅ | — | — | — | ✅ |

1. Corretto **dall'audit**: avevo usato `--line-base` (1px) come `gap` della
   griglia. Un peso di linea non è una spaziatura.
2. Solo l'eccedenza oltre la soglia §16 è calda, più due tacche e due numeri.
   Nella prima versione l'intero arco diventava rosso: due quadranti su tre
   erano interamente caldi.
3. **Scostamento dal riferimento, deciso**: la tavola del riferimento è quasi
   tutta rossa. Qui il colore dice il blocco (s/p/d/f) sui gradini di ciano.
4. Il terminatore solare e la sua etichetta: una linea e una riga.
5. Riscritti per densità — vedi «Riscritture».
6. Gli anelli girano **solo** quando l'agente lavora, verificato a runtime: 4
   anelli su 5 si muovono con `attivo: true`, **0 su 5** con `attivo: false`.
   Il quinto è la ghiera fissa, immobile in entrambi i casi.
7. I contatori interpolano solo all'arrivo di un campione nuovo.
8. Il campo scorre solo quando arrivano byte.
9. **Deroga dichiarata** — vedi «Il testo in WebGL».

---

## Riscritture, cioè il ciclo §11.7 che funziona

Nessuna di queste sarebbe stata trovata leggendo il codice.

**Gli anelli uscivano dal pannello.** Un elemento sostituito con rapporto
d'aspetto intrinseco e quattro `inset` assoluti è sovravincolato, e Chromium
scioglie il conflitto a modo suo: il disco veniva scalato sulla larghezza e
passava sopra il piede.

**Le linee di costruzione degli anelli erano rumore.** Erano otto raggi dal
centro alle spallette dei varchi, ad angoli scorrelati: sembravano casuali,
cioè esattamente ciò che §11.6 regola 6 vieta. Sostituite con la circonferenza
primitiva a metà fascia, che è la quota del disegno meccanico.

**Gli anelli erano quattro cerchi, non un disco.** Fasce distanti, tick che
galleggiavano nel vuoto. Rifatti adiacenti, con una ghiera fissa interna che
chiude il centro e fa da scala di riferimento.

**I quadranti sembravano un cruscotto.** Arco del valore spesso 7 mm: era
l'elemento più pesante del pannello. Portato a 3 mm, e il caldo ristretto
all'eccedenza.

**Lo screenshot dei quadranti mostrava numeri mai esistiti** — 88,8 invece di
92,6 — colti a metà dell'interpolazione. Ora il montaggio aspetta che i
contatori si fermino: il ciclo §11.7 deve giudicare uno stato fermo.

**La nuvola di punti usciva da tutti e quattro i lati.** La distanza della
camera era un multiplo del raggio scritto a mano. Ora si calcola dal campo
visivo, **vertice per vertice**: inquadrare il bounding box lascerebbe fuori
gli spigoli vuoti di una sfera, e l'oggetto resterebbe piccolo in mezzo.

**Un'etichetta della nuvola sbordava sulla legenda.** Misurata prima che i font
arrivassero: `offsetWidth` col font di ripiego dà un'altra larghezza. Ora si
riposiziona su `document.fonts.ready`.

**Il cavo T1 → T2 era un moncone di otto pixel.** Due nodi incolonnati
collegati come se fossero affiancati. Risolto dando a T2 una colonna propria:
ogni arco corre in orizzontale, come il flusso.

**Il campo di glifi era invisibile.** Il riempimento predefinito del testo in
PixiJS è **nero**, e la tinta moltiplica: ogni colore dava nero. Trovato
misurando i pixel dello screenshot, non guardandolo — a occhio sembrava solo
«un po' scuro».

**Il campo di glifi era una griglia 1×1.** Misurava il contenitore mentre era
ancora `display: none`. Ora nasce al primo byte.

---

## Scostamenti dalla specifica, dichiarati

### ⚠️ Tre librerie di §22 non sono entrate

Installate, misurate e **rimosse**, ognuna per un invariante:

| Libreria | Perché no |
|---|---|
| **three-globe** | genera geometria propria: non estende `ParametricComponent`, non usa `segmentsFor()`, non passa `qualityGate()` — invariante 22. E il layer archi, che è ciò per cui vale, non ha coordinate vere (R39). 25 MB, 18 dipendenze |
| **troika-three-text** | rasterizza testo in WebGL (invariante 20) e vuole colore e font come **letterali** (invariante 18). Le etichette 3D sono `<span>` proiettati dalla scena |
| **d3-force** | una simulazione a molle si assesta muovendosi: animazione ambientale, invariante 25. §11.5 concede esplicitamente «layout fisso» |

Restano `three`, `animejs`, `pixi.js`, `d3-shape`. Costo misurato:
**22 → 38 pacchetti**, `ui/vendor/` da 0,9 a 2,0 MB. Con le tre rimosse
sarebbero stati 84 pacchetti e 510 MB in `node_modules`.

### ⚠️ Il testo in WebGL — una deroga, non due

L'invariante 20 vuole il testo nel DOM; §11.4 assegna «glifi di massa e log
scorrevoli» a PixiJS e §22 li mette in questa fase. La riga che separa i due
casi è nella §11.4 stessa: il testo che si **legge** — pannelli, tabelle,
etichette — resta DOM; una massa di mille glifi non si legge, si **guarda**.
È per la stessa distinzione che le etichette di globo e nuvola sono DOM
proiettato e non troika.

### ⚠️ `Math.random()` fuori dalla nuvola di punti

§17.4 prende `u` da `Math.random()` e §11.10 regola 4 lo concede alle nuvole.
Qui `u` viene dall'**hash del percorso del file**: stessa distribuzione, stessa
inversione `acos(2u−1)`, ma ogni punto è un file che si può nominare e la
posizione è stabile fra un render e l'altro. Le fasce di latitudine sono le
cartelle di primo livello, di area proporzionale al numero di file.

### ⚠️ `core/tools/geo.py` non è in §21.1

Il tool `timezones`. Il renderer non può leggere `/usr/share/zoneinfo`
(invariante 1), quindi passa dall'allowlist (invariante 2). **Non ha
parametri**: il percorso è una costante del modulo, quindi nessun input può
spostarlo — difesa strutturale, non una validazione da ricordarsi.
`side_effect=False`, nessuna conferma richiesta.

### ⚠️ I periodi di §10.3 non erano usabili come sono

«46/74/120/240 s, mai multiple tra loro» — ma 240 = 2 × 120, e i due anelli si
riallineerebbero ogni 240 s esatti. Tengo 46, 74, 120 e porto l'ultimo a
**233 s**.

### ⚠️ Nessuna texture della Terra, nessun arco sul globo

Le immagini di three-globe non hanno licenza dichiarata nel pacchetto, e la
regola 30 vuole licenza **verificata**. Al loro posto ci sono i 312 fusi veri:
i continenti si disegnano da dove la gente tiene l'ora. Gli archi del
riferimento restano assenti finché non ci sarà una sorgente di coordinate vere
(Fase 8).

---

## Tre difetti del quality gate di §11.11, trovati facendolo girare

**① «Geometria degenere» bocciava il `ReactorRing` di §11.10.** §11.11 fallisce
se una dimensione del bbox è zero — ma l'anello che §11.10 dà come esempio è
piatto per costruzione. Ora la degenerazione dipende da quante dimensioni sono
nulle e da quante il componente ne dichiara: un 2D **deve** essere piatto, un
3D non deve esserlo. Più severo di prima, non meno.

**② La regola 7 di §11.10 non era imposta da nessuno.** «Bounding box
dichiarato e verificato»: il gate controllava solo che non fosse assurdo
(< 5000 mm), quindi vedeva un errore di ordini di grandezza ma non uno del
doppio. Ora `meta.bbox` è obbligatorio e verificato, e per i quadranti e il
terminatore è calcolato **in forma chiusa**, indipendente dal ciclo di
`build()` — altrimenti sarebbe una tautologia.

**③ Un componente traslato via passava indisturbato.** Aggiungere 9000 mm a un
asse non cambia nessuna estensione: il gate approvava, e il componente finiva
fuori inquadratura. Trovato da `tests/eval_visual.py`, che prova il gate con
guasti veri. Ora il centro del bbox deve stare vicino all'origine: la
collocazione è della composizione, non della geometria.

---

## Il tranello che mi ha preso tre volte

Un **backtick dentro un commento CSS** chiude il template literal che contiene
il foglio di stile del componente, e il modulo smette di caricarsi. Sintomo:
pagina bianca ed errore di console che sembra un problema di import map.

Adesso `tests/eval_visual.py` copia ogni `.js` di `ui/src/` in `.mjs` e lo fa
analizzare da `node --check`: `node --check` su un `.js` lo legge come CommonJS
e non basta. Verificato che il controllo scatti sul guasto vero.

---

## ❌ NON VERIFICATO

1. **60fps su un'altra macchina.** Misurato su questa: AMD Radeon 860M,
   Wayland, direct rendering. Su una GPU diversa il numero è un altro.
2. **Il comportamento con la finestra a schermo intero e più pannelli aperti
   insieme.** Il banco fa girare tre motori in tre riquadri da 300 px; la
   scrivania di §13 li avrà più grandi e più numerosi. La disposizione delle
   finestre è §13, non questa fase.
3. **La mesh agenti con T1 e T2 davvero collegati.** L'engine non li compone —
   vivono nella pipeline vocale — e il pannello lo dice: `non collegato`. Il
   percorso con dati vivi si verifica quando le due radici di composizione
   saranno una sola (Fase 9).
4. **La galleria in Electron.** Il banco `--bench` carica `gallery.html` da
   `file://` e funziona; gli altri componenti sono stati giudicati sul server
   di sviluppo, come da Fase 0b.
5. **`--bench` con la finestra non massimizzata.** Le misure sono a finestra
   massimizzata su 3840×2160.

---

## Riepilogo

| | |
|---|---|
| Test | **223 verdi** (erano 218) + **133** negli eval |
| Componenti nuovi | 7, tutti col ciclo §11.7 |
| Geometrie parametriche | 6, tutte gatate |
| Correzioni al quality gate | 3, tutte trovate facendolo girare |
| Riscritture dopo screenshot | 10 |
| Budget di frame | **dentro**, 59,9 fps con tre motori insieme |
| Dipendenze aggiunte | 4 (three, animejs, pixi.js, d3-shape) |
| Dipendenze scartate dopo prova | 3, ognuna per un invariante |
