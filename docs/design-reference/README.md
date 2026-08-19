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

## COSA GUARDARE, riquadro per riquadro

Questa sezione e' nata da una revisione del 19 agosto 2026 che ha confrontato
`shots/scrivania/ws-01..04.png` con questi riferimenti **misurando i pixel**.
Ogni riga dice quale immagine aprire, dove guardare, e la soglia numerica da
raggiungere. Vedi `docs/DIVARIO-PREMIUM.md` per il metodo.

### Barra superiore — `01` fascia 0–19px · `05` fascia 0–15px · `10` fascia 0–15px

Le tre immagini concordano, ed e' il caso piu' istruttivo di tutto il set.

| | altezza | inchiostro (L>50) | luminanza media |
|---|---|---|---|
| `01-desktop-mcu-completo` | 3,4 % | **28,4 %** | 51 |
| `05-dashboard-news` | 3,3 % | **35,1 %** | 52 |
| `10-globo-gps-locator` | 3,3 % | **37,0 %** | 56 |
| **`shots/scrivania/ws-01`** | 4,3 % | **2,8 %** | **19** |

**La nostra barra e' gia' PIU' ALTA del riferimento e dieci volte piu' vuota.**
Non va ingrandita: va riempita, e semmai abbassata al 3,3 %.

Cosa contiene la barra nel riferimento, e che noi non mostriamo:

- una fascia **piena** `#1a1f23` (L 30), non una riga di contorno su nero;
- decine di micro-etichette a corpo minimo — sigle, contatori, orari, stati di
  modulo — allineate su una sola linea di base;
- gruppi separati da divisori verticali hairline, non da spazio vuoto;
- in `10`, la barra e' su **due righe**: sigle sopra, valori sotto.

Il dato per riempirla **esiste gia'** in `state.snapshot` e finisce oggi in un
solo pannello: numero di tool in allowlist, client collegati, uptime, byte sul
socket, fase, PID, stato di ogni provider vocale, seccomp.

**Soglia**: inchiostro L>50 nella fascia della barra **≥ 25 %**.

### Dock inferiore — `01` fascia 520–563px · `05` fascia 435–450px

| | altezza | inchiostro (L>50) | luminanza media |
|---|---|---|---|
| `01-desktop-mcu-completo` | 7,6 % | **26,2 %** | 39 |
| `05-dashboard-news` | 3,3 % | **22,8 %** | 33 |
| **`shots/scrivania/ws-01`** | 4,3 % | **2,8 %** | 20 |

In `01` il dock e' **il doppio piu' alto** della barra e porta cinque icone
grandi, geometriche, monocrome — non pulsanti di testo. A destra e a sinistra
del gruppo di icone ci sono fasce di micro-etichette che continuano la barra.

**Soglia**: inchiostro L>50 **≥ 20 %**.

### Superfici piene — `01` riquadro `BUSINESS` · `01` calendario · `05` colonna `MARKET DATA`

E' il divario piu' grande dell'intera revisione: riferimento **42 %** di pixel
riempiti (L>60), nostra scrivania **4,5 %**.

Guardare in particolare:

- `01`, riquadro `BUSINESS`: **blocco pieno** `#336276` (L 89). Non un pannello
  con bordo: una superficie.
- `01`, calendario centrale: ogni cella e' **piena** — `#4d6d78` (L 103) per la
  griglia, `#61868f` (L 127) per l'evidenza. La cella di oggi e' rossa, ed e'
  l'unico rosso della schermata.
- `05`, colonna `MARKET DATA`: righe alternate su fondo pieno, con il valore in
  monospace a destra. E' esattamente la forma che devono prendere le nostre
  tabelle.

**Soglia**: pixel L>60 **≥ 25 %** per workspace.

### Accento caldo — `01` colonna cartelle sinistra · `01` riquadro `CIRCA COMPANY`

Riferimento **5,70 %** di pixel caldi, nostra scrivania **0,00 %**.

Nel riferimento il caldo **non e' l'allarme**. E':

- le cartelle manila `#b48d64` (L 146), una dozzina, in tre punti diversi;
- il riquadro `CIRCA COMPANY`, riempito di manila;
- gli archi arancioni sulla mappa dei collegamenti, in `01` e in `05`.

L'allarme e' una sola cosa: **una cella rossa nel calendario**, in `01`. E in
`05` il ticker `DOW JONES` in negativo su fondo rosso — un blocco solo.

**Soglia**: pixel caldi fra **3 % e 6 %** per workspace, dei quali il rosso
critico resta sotto l'1 %.

### Colonne laterali persistenti — `01` sinistra · `05` sinistra · `10` sinistra

In tutte e tre le immagini c'e' una colonna sempre presente a sinistra, e non
cambia col contenuto:

- `01`: due alberi sovrapposti, `FAVORITES`/`FOLDERS` e `ELEMENTS`, con
  checkbox e indentazione;
- `10`: `GPH_V02 COORDINATES` con mini-mappa, `VOICE EQUALIZER`, e la coppia di
  coordinate in monospace grande;
- `05`: la colonna del sito incassato, con la sua barra di ricerca vera.

E' cio' che da' all'insieme l'aria di un sistema operativo invece che di un
cruscotto. Il dato c'e' gia': `fs.list` e `source.tree`.

### Contenuto media — `01` quattro player · `05` player + griglia miniature

E' il motivo per cui il 17,4 % dei pixel del riferimento sta sopra L=120, e la
nostra scrivania e' all'1,3 %. Materiale fotografico: denso, chiaro, con un
bordo netto.

- `01`: quattro riproduttori con barra di trasporto, piu' una webcam;
- `05`: un player grande con sottotitolo su fascia piena, una **griglia 8×2 di
  miniature** in basso a sinistra, e tre schede storia con anteprima.

Noi abbiamo testo, SVG, three.js e una `<webview>` che nessuno apre.

### Equalizzatore vocale — `10` riquadro sinistro `VOICE EQUALIZER`

Riferimento diretto per la Fase 3. Istogramma a barre su fondo pieno, in rosso,
con sotto il valore in monospace grande (`12:48.14`), `60 Hz`, `220 VOLTS`.
**Dati veri dal microfono**, non un'animazione: §11.9.

### Elemento centrale dominante — `10` globo · `06` nuvola di punti

Riferimento per §25, lo strato di presenza. In `10` il globo occupa il 45 %
della larghezza ed e' **circondato** dal chrome, non coperto. In `06` la sfera
di punti fa lo stesso.

⚠️ **Nota per §25**: nessuna delle dodici immagini ha un elemento centrale
**dietro** ai pannelli. Il nucleo di §25 e' una scelta consapevole che si
discosta dal riferimento, ed e' documentata li'.

### Cornici e tagli — tutte le immagini

- Il taglio a 45° e' su **uno o due vertici**, mai zero e mai quattro.
- I bordi sono hairline, e cambiano peso **solo** per marcare il fuoco.
- In `10` e `11` la cornice esterna ha un tratto piu' spesso su **un solo lato**
  — e' asimmetria progettata, non un errore.

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

### Dal 19 agosto 2026, un passo in piu'

7. esegui `scripts/densita.mjs` sullo screenshot e riporta le tre misure —
   pixel L>25, pixel L>60, pixel caldi — contro le soglie della sezione
   «COSA GUARDARE» qui sopra.

Il passo 7 esiste perche' il passo 5 non basta: la revisione del 19 agosto ha
mostrato che dodici componenti giudicati conformi a occhio erano **nove volte**
sotto il riferimento in densita' di superficie. La checklist §11.8 non aveva una
domanda che potesse accorgersene.
