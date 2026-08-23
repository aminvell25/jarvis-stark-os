# Riferimenti visivi — JARVIS OS

Leggere questo file **prima** di ogni componente visivo.

I riferimenti si dividono in **quattro famiglie**, e la distinzione e' la cosa
piu' importante di questo documento: dice che cosa si puo' prendere da
un'immagine e che cosa no.

| | Che cos'e' | Che cosa se ne prende |
|---|---|---|
| **famiglia-a** | information design cinematografico | tutto: forma, densita', trattamento |
| **famiglia-b** | asset stock con bloom e alone | **niente** — al massimo una forma, ridisegnata |
| **famiglia-c** | sistemi operativi veri, con un tema | l'anatomia, mai il trattamento |
| **famiglia-d** | proposte nostre, fatte con Claude Design | le **decisioni di layout**, mai i valori letterali |

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
| `02-oggetti-3d-in-pannelli.png` | **chiave per il 3D**: primitive wireframe con linee di costruzione, isolate in pannelli etichettati `ver 1..10`, densita' linee variabile con la curvatura | §11.10 ParametricComponent |
| `03-database-tabellare-denso.png` | densita' tabellare, righe evidenziate, monospace | file manager, pannelli dati |
| `04-analisi-armatura-grafo-nodi.png` | **grafo a nodi** con linee ortogonali e raccordi | mesh agenti, §13 |
| `05-dashboard-news.png` | player incassato, lista storie, mappa con archi, ticker rosso | pannello news, §15 |
| `07-griglia-9up-con-web-incassato.png` | **chiave webview**: pagine web reali dentro i pannelli (barra URL visibile) | §6.3 |
| `08-archivio-piani-stratificati.png` | **chiave CSS 3D**: documenti su piani Z traslucidi, filmstrip di miniature | §11.4 — NON three.js |
| `10-globo-gps-locator.png` | globo con archi, chrome piatto attorno, equalizzatore vocale | three-globe + d3-geo |
| `12-logo-anelli-concentrici.png` | anelli **concentrici** (scarti < 1,7 % del raggio, misurati), fasce piene e adiacenti che coprono **0,484 del raggio**, tick, **e il marchio `J.A.R.V.I.S.` al centro con un filetto sotto** | §11.10 ReactorRing, §25.13 |

> ⚠️ **Il marchio è stato aggiunto a questa riga il 22 agosto 2026, e l'omissione
> è costata un errore.** La descrizione diceva solo «anelli, tick, centri», e
> con quella descrizione ho chiesto di rimuovere dal nucleo una scritta che il
> riferimento **ha**. Una riga che elenca tre cose su quattro sembra completa:
> è il modo in cui un elenco mente senza dire una parola falsa. Chi aggiunge
> un'immagine qui elenchi anche ciò che gli sembra ovvio.

> **Nove file, non dodici — ed e' voluto.** Il 20 agosto 2026 il proprietario
> ha tolto `06-access-server-trace-archive`, `09-board-investigativa-3d` e
> `11-tavola-periodica-scanner`, e ha rinominato la `02`. I componenti che
> nascevano da quelle tre — nuvola di punti, board in CSS 3D, tavola periodica
> — **sono gia' costruiti e verificati**: le immagini avevano finito il loro
> lavoro. Restano nella cronologia di git per chi dovesse rifarli.
> Nota scritta qui perche' un elenco che si accorcia senza spiegazione sembra
> una perdita, non una decisione.

---

## COSA GUARDARE, riquadro per riquadro

Questa sezione e' nata da una revisione del 19 agosto 2026 che ha confrontato
`shots/scrivania/ws-01..04.png` con questi riferimenti **misurando i pixel**.
Ogni riga dice quale immagine aprire, dove guardare, e la soglia numerica da
raggiungere. Vedi `docs/DIVARIO-PREMIUM.md` per il metodo.

> ### ⚠️ UN NUMERO IN PIXEL DEL RIFERIMENTO NON E' UN BERSAGLIO
>
> Aggiunto il 22 agosto 2026, dopo che lo stesso errore e' costato due volte.
>
> Le immagini di famiglia-a sono **901 x 563**; la nostra finestra e'
> **1536 x 843**. Un numero letto sul riferimento e riportato tale e quale da
> noi vale quindi 1,7 volte di meno in orizzontale e 1,5 in verticale:
>
> ```
> Kx = 1536 / 901 = 1,705      Ky = 843 / 563 = 1,497
> ```
>
> **Ogni misura che attraversa il confine va espressa in percentuale** della
> larghezza o dell'altezza del riquadro che la contiene, mai in pixel. Il
> pixel e' l'unita' in cui si MISURA, la percentuale e' quella in cui si
> TRASFERISCE.
>
> I due casi in cui e' andata storta, entrambi nel catalogo:
>
> | letto sul riferimento | trasferito come | ma vale | e quindi |
> |---|---|---|---|
> | tessera **28 x 14 px** | «20 x 20 px» | 28 px e' l'**8,2 %** della larghezza di quel pannello (342 px) | sul nostro da 605 px la tessera e' **50 x 33**, non 20 x 20 — e nel passaggio il rettangolo 2:1 e' diventato anche un quadrato |
> | icona del plinto **40 px** | «40 px» | il **4,4 %** della larghezza dell'immagine | sui nostri 1536 sono **68 px**, non 40 |
>
> Regola operativa: quando si scrive un numero preso da qui, si scrive accanto
> **di che cosa e' la percentuale**. Un numero senza denominatore e' un numero
> che il prossimo trasferimento sbagliera' di nuovo.

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

### Elemento centrale dominante — `10` globo

Riferimento per §25, lo strato di presenza. Il globo occupa il 45 % della
larghezza ed e' **circondato** dal chrome, non coperto.

⚠️ **Nota per §25**: nessuna delle dodici immagini ha un elemento centrale
**dietro** ai pannelli. Il nucleo di §25 e' una scelta consapevole che si
discosta dal riferimento, ed e' documentata li'.

### Cornici e tagli — tutte le immagini

- Il taglio a 45° e' su **uno o due vertici**, mai zero e mai quattro.
- I bordi sono hairline, e cambiano peso **solo** per marcare il fuoco.
- In `10` e `11` la cornice esterna ha un tratto piu' spesso su **un solo lato**
  — e' asimmetria progettata, non un errore.

---

## famiglia-c/ — STRUTTURA SÌ, TRATTAMENTO NO

> ⚠️ **La cartella non esiste ancora**: l'immagine va salvata come
> `famiglia-c/01-windows-7-tema-jarvis.png`. La regola sotto vale da quel
> momento.

Aggiunta il 19 agosto 2026. Sistemi operativi **veri** con un tema applicato.

**La regola, e non ha eccezioni:**

> Da famiglia-c si prende **come è organizzata una cosa** — l'anatomia di una
> finestra, l'ordine dei controlli, dove va il conteggio degli elementi.
> Non si prende **mai come è disegnata**: né glow, né gradienti, né angoli
> tondi, né la sua densità.

Perché la distinzione esiste: questi non sono progetti grafici, sono **pelli**.
Sotto c'è il layout di Microsoft, con le sue spaziature e la sua densità bassa.
Copiare l'aspetto significa ereditare quella densità, che è l'opposto di ciò
che insegna famiglia-a.

| File | Cosa se ne prende | Cosa si RIFIUTA |
|---|---|---|
| `01-windows-7-tema-jarvis.png` | **anatomia del file manager**: `« » ▾ percorso ▾ ⟳ [cerca]`, riga strumenti (`Organizza / Includi / Condividi / Nuova cartella`), albero `Preferiti / Raccolte / Computer` a sinistra, **conteggio elementi nel piede** (`11 elementi`, `46 elementi`) · anatomia della barra applicazioni a piena larghezza: lanciatore a sinistra, pulsanti attività, orologio a destra in cornice | glow su ogni icona · gradienti verticali nei corpi · angoli arrotondati · blu saturo · Segoe UI proporzionale con numeri non monospace · icone 3D con riflessi · margini enormi nel Pannello di controllo |

**Il conteggio nel piede** merita una riga a parte: è l'invariante 23 applicata
da vent'anni. Si dichiara **sempre** quanti elementi ci sono, anche zero.

⚠️ `01-windows-7-tema-jarvis.png` mostra una barra **a piena larghezza e
ancorata** — l'opzione A del confronto di §26.3. Il progetto ha scelto
l'opzione **B**, il pannello centro-basso di `famiglia-a/01`. Le due immagini
mostrano due modelli diversi: quello di famiglia-c serve per l'anatomia del
file manager, non per la forma della barra.


---

## famiglia-d/ — DECISIONI SI', VALORI NO

Aggiunta il 21 agosto 2026. Non e' un riferimento esterno: e' un mockup
**nostro**, prodotto con Claude Design a partire da questo stesso codice.

**La regola, e non ha eccezioni:**

> Da famiglia-d si prendono le **DECISIONI di layout** — che cosa sta dove, in
> che proporzione, sopra a che cosa. Non si prendono **mai i valori
> letterali**: ogni colore, spaziatura e corpo tipografico deve arrivare da
> `tokens.css`, e un valore che non vi corrisponde si propone come token nuovo
> con la propria luminanza misurata, non si copia.

Perche' la distinzione esiste, e perche' non e' la stessa di famiglia-c: un
mockup nostro parla gia' la nostra lingua, e questo lo rende **piu'** insidioso
di uno stock, non meno. Sembra conforme perche' e' costruito con i nostri
componenti, e le poche cose che conforme non sono — quattro colori scritti a
mano, un corpo tipografico derivato per moltiplicazione, un'animazione senza
causa — passano inosservate proprio perche' tutto il resto e' a posto.

| File | Cosa se ne prende | Cosa si RIFIUTA |
|---|---|---|
| `01-scrivania-viva.png` | lo **strato di presenza** di §25 dietro i pannelli, con lo stato dell'agente letto dalla forma e non da un'etichetta; la **fascia di lettura grande** e la **tabella densa** come modo di riempire (§10.5) | i quattro colori letterali della nuvola · il sesto corpo tipografico ottenuto con `calc(--t-title * 2.4)` · la rotazione continua, che e' animazione ambientale (invariante 25) e costa **10,2 ms per fotogramma** misurati |

La misura di ogni voce sta in `docs/acceptance/MOCKUP-SCRIVANIA-VIVA.md`.

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

### Dal 22 agosto 2026, un passo accanto — non uno in piu'

8. esegui `node scripts/densita.mjs --traboccamento <url> [larghezza]` ad
   **almeno due larghezze** — quella di lavoro e una stretta — e riporta il
   contenuto tagliato.

⚠️ **Va letto INSIEME al passo 7, non dopo.** La densita' premia l'inchiostro;
il traboccamento dice quanto di quell'inchiostro e' contenuto **cancellato**.
Le due si separano proprio dove fa piu' male, e non e' un'ipotesi: la barra di
§13 misurava il 63 % di inchiostro nella propria fascia — piu' del doppio della
soglia — **mentre** a 1024 px di finestra teneva 437 px di campi in 285
disponibili con `overflow: hidden`. Il 153 % in piu' di contenuto di quanto ce
ne stesse, tagliato e senza nessun gesto per riprenderlo: `up`, `rx` e la scena
non esistevano, e la misura di densita' la promuoveva.

Che cosa conta come traboccamento e che cosa no:

| `overflow` | il contenuto | conta? |
|---|---|---|
| `auto` / `scroll` | eccede e si RAGGIUNGE | **no** |
| `hidden` / `clip` | e' CANCELLATO senza rimedio | **si** |
| `visible` | esce e si sovrappone | e' un altro difetto, non questo |

**Soglia: zero.** Non c'e' una percentuale accettabile di contenuto cancellato:
o si raggiunge, o non c'e'.
