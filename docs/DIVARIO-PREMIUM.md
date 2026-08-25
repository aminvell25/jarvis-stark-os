# Divario verso il riferimento — analisi misurata

**Data**: 19 agosto 2026 · **Base**: commit `feat(§13): la scrivania`
**Confronto**: `docs/design-reference/famiglia-a/01-desktop-mcu-completo.png`
contro `shots/scrivania/ws-01..04.png`

Questo documento non contiene opinioni sul gusto. Contiene misure fatte sui
pixel dei due lati del confronto, e per ogni scarto una correzione dichiarata.

---

## 0. La misura che riassume tutto

> ### ⚠️ Questa tabella è del 19 agosto e misura un mondo che non c'è più
>
> `WS01…WS04` sono i **quattro workspace**, che **ADR-010 ha abolito il 19
> agosto**: oggi c'è una scrivania sola e `Alt+1…4` filtra invece di cambiare
> pagina. Gli scatti `shots/scrivania/ws-0*.png` non vengono più rigenerati.
>
> La tabella resta perché è la diagnosi che ha aperto questo documento, e la
> **colonna del riferimento è ancora il bersaglio**. I numeri nostri no. Lo
> stato corrente sta in `docs/PIANO-CORE-E-DENSITA.md` §9, misurato col
> protocollo del turno 1 su `shots/scrivania/scrivania.png`:
>
> | | ent | dev | L>60 | caldo | fondo nudo |
> |---|---|---|---|---|---|
> | riferimento | 3,32 | 55,7 | 42,1 % | 5,70 % | 21,9 % |
> | **23 ago, `b2f7360`** | **1,69** | ~20 | **10,0 %** | 0,2 % | ~37 % |
>
> Due metriche di questa tabella sono state **ritirate dal giudizio** e restano
> come contesto: `L>25` (rev 5.10, satura) e la luminanza media da sola. Il
> giudizio lo fanno entropia dell'istogramma e deviazione standard.

Luminanza percepita (Rec. 709) su tutta l'immagine, riferimento contro scrivania.

| Metrica | Riferimento | WS01 | WS02 | WS03 | WS04 |
|---|---|---|---|---|---|
| Luminanza media (0–255) | **68,65** | 24,45 | 21,42 | 20,51 | 23,27 |
| Pixel non-neri (L>25) | **78,12 %** | 15,12 % | 8,54 % | 7,08 % | 10,97 % |
| Pixel riempiti (L>60) | **42,09 %** | 4,46 % | 1,89 % | 1,50 % | 2,44 % |
| Pixel chiari (L>120) | **17,36 %** | 1,33 % | 0,81 % | 0,84 % | 0,82 % |
| Saturazione media | 0,349 | 0,387 | 0,364 | 0,400 | 0,374 |
| Pixel caldi (r > b+15) | **5,70 %** | 0,00 % | 0,01 % | 0,07 % | 0,50 % |

**Lettura.** La saturazione è allineata: la disciplina cromatica è corretta e non
va toccata. Tutto il resto no. Il riferimento ha **nove volte** la superficie
riempita, e il nostro accento caldo è a zero contro il 5,7 % del riferimento.

Il difetto non è «la UI è brutta». È: **disegniamo contorni luminosi sul nero,
il riferimento dipinge superfici a media luminosità su grigio scuro.**

---

### ⚠️ `L>25` è stata RITIRATA dal giudizio (rev 5.10)

La riga «pixel non-neri» resta qui perché è la misura che ha aperto questa
analisi, ma **non è più un criterio.** Alla rev 5.9 le superfici di base sono
salite da L 18 a L 31 e `L>25` è passata da 15,12 % a **96,9 %** — sopra il
riferimento, che sta al 78,12 %.

Da quel momento non poteva più bocciare niente: la supera qualunque schermata
con un fondo sopra L 25, **compresa una schermata di un colore solo.** Una
metrica satura è peggio di nessuna metrica, perché passa sempre e sembra una
verifica.

Al suo posto due misure che una superficie uniforme non può ingannare:

| | cosa chiede | massimo |
|---|---|---|
| **deviazione standard** | quanto la luminanza si allontana dalla propria media | — |
| **entropia** dell'istogramma a 16 bin | quanto i livelli sono distribuiti, in bit | 4,00 |

Non chiedono «quanto è acceso» ma **«quanto è articolato»**, che è la domanda
a cui `L>25` non sapeva rispondere. Misurate su tutti e tre i riferimenti e
sulla scrivania di oggi:

| | lum | **dev.std** | **entropia** | 25–120 | L>60 | L>120 | caldo | barra |
|---|---|---|---|---|---|---|---|---|
| **soglia** | — | **≥ 32** | **≥ 2,40** | — | **≥ 25 %** | — | 3–6 % | ≥ 25 % |
| `famiglia-a/01` | 68,7 | **55,7** | **3,32** | 60,8 % | 42,1 % | 17,4 % | 5,7 % | 28,4 % |
| `famiglia-a/10` | 58,9 | **41,9** | **3,05** | 71,2 % | 34,8 % | 11,4 % | 0,4 % | 37,0 % |
| `famiglia-a/05` | 45,7 | **40,6** | **2,85** | 50,9 % | 24,0 % | 7,0 % | 3,7 % | 35,1 % |
| ws-01 · rev 5.7 | 24,6 | 20,6 | 1,34 | 14,6 % | 4,6 % | 1,5 % | 0 % | 3,3 % |
| ws-01 · rev 5.9 | 36,2 | **18,7** | **1,25** | 95,1 % | 5,4 % | 1,8 % | 0 % | 4,5 % |
| ws-01 · rev 5.10 | 36,5 | 19,1 | 1,29 | 95,1 % | 6,0 % | 1,8 % | 0,1 % | 6,0 % |

Le soglie stanno **a metà strada** fra la nostra rev 5.7 e il più povero dei
tre riferimenti, `famiglia-a/05`: dev.std fra 20,6 e 40,6 → **32**; entropia
fra 1,34 e 2,85 → **2,40**.

**E dicono una cosa che le altre metriche non dicevano.** Dalla 5.7 alla 5.9
l'entropia è **scesa** — 1,34 → 1,25 — e con lei la deviazione standard. Il
lavoro sui token ha spostato il 71 % dei pixel da un picco a L 18 a un picco a
L 31: più chiari, **ugualmente monotoni**. La luminanza media è salita di
dodici punti e l'articolazione è peggiorata. È la stessa diagnosi di §1 e §2
vista da un terzo angolo, ed è il motivo per cui il lavoro vero è §2 e non la
palette.

---

## 1. Palette — manca tutta la banda media · IMPATTO MASSIMO

**Riferimento visivo**: `famiglia-a/01`, riquadro `BUSINESS` (blu pieno) e
riquadro `CIRCA COMPANY` (manila pieno) · `famiglia-a/05`, colonna
`MARKET DATA`.

### La prova

Luminanza dei colori dominanti, misurata sulle due immagini.

| Riferimento | L | Ruolo osservato |
|---|---|---|
| `#0f1418` | 19 | fondo scrivania |
| `#1a1f23` | 30 | banda della barra superiore, **piena** |
| `#13212a` | 31 | riempimento di pannello scuro |
| `#1e2631` | 37 | riempimento di pannello |
| `#32464f` | 66 | riempimento di cella / riga |
| `#336276` | 89 | riempimento di pannello **acceso** (BUSINESS) |
| `#4d6d78` | 103 | cella di calendario piena |
| `#61868f` | 127 | cella di calendario in evidenza |
| `#b48d64` | 146 | cartella manila |

| `tokens.css` oggi | L | Come lo usiamo |
|---|---|---|
| `--bg-void` `#070b0d` | 10 | fondo |
| `--bg-deep` `#0a1014` | 15 | barra e dock |
| `--bg-panel` `#0e1315` | 18 | corpo pannello |
| `--bg-raised` `#131a1d` | 25 | rilievo |
| `--cy-900` `#123840` | 48 | **solo bordo** |
| `--cy-700` `#1f6b78` | 92 | tratto |
| `--cy-500` `#4dd0e1` | 181 | testo e dato |

**Fra L=25 e L=181 non esiste un solo token che usiamo come RIEMPIMENTO.**
Il riferimento vive per intero in quella banda. Il nostro salto è di 156 punti
di luminanza fatto in un pixel di bordo — per questo l'insieme legge come un
wireframe e non come una plancia.

### La correzione

> ⚠️ **Riscritta il 19 agosto 2026 (rev 5.9).** La prima stesura prescriveva
> **sei** riempimenti da mettere *accanto* alle superfici esistenti. Era
> l'analisi giusta e la leva sbagliata, e la misura di questo stesso documento
> lo diceva già: **il 71,2 % della scrivania è `--bg-panel`** e solo il 2,4 %
> è il fondo. I due riempimenti più bassi — L 31 e L 37 — erano duplicati di
> `--bg-panel` e `--bg-raised` alla luminanza giusta. Non serviva un token
> accanto: serviva spostare quello che c'era. Vedi
> `docs/acceptance/TOKENS-RIEMPIMENTO.md`.

Il riferimento **non ha una scala monotona.** Ha tre registri:

| registro | L | cosa ci sta |
|---|---|---|
| pavimento | 19 | la scrivania, e nient'altro |
| **banda di superficie** | 30–37 | barra, dock, pannelli, rilievi |
| riempimenti di stato | 66–146 | solo dove c'è uno **stato** da dire |

Barra e pannello stanno nella **stessa** banda: nel riferimento la barra si
distingue per densità d'inchiostro — decine di micro-etichette su una linea di
base — non per il fondo.

```css
/* le superfici di base salgono nella banda misurata */
--bg-void:#0f1418;    /* L  19  pavimento — il fondo del riferimento     */
--bg-deep:#1a1f23;    /* L  30  barra e dock, misurato su famiglia-a/01  */
--bg-panel:#13212a;   /* L  31  corpo del pannello — il 71 % dei pixel   */
--bg-raised:#1e2631;  /* L  37  rilievo, riga alternata                  */

/* e TRE riempimenti, che dicono uno stato e non una superficie */
--fill-1:#32464f;   /* L  66  cella attiva, intestazione di tabella      */
--fill-2:#336276;   /* L  89  pannello acceso, selezione                 */
--fill-3:#4d6d78;   /* L 103  evidenza dentro una griglia densa          */
--manila:#b48d64;   /* L 146  cartelle e contenitori — vedi §4           */
```

Misurato dopo: `L>25` sulla scrivania passa da **16,4 % a 96,9 %** senza che
nessun componente sia stato toccato, perché il 71 % dei pixel ha cambiato
luminanza da 18 a 31. `L>60` resta a 5,5 %: i riempimenti di stato non li usa
ancora nessuno, ed è il lavoro di §2.

⚠️ **Il costo lo paga il testo.** Alzare `--bg-panel` di 13 punti abbassa il
contrasto di tutto ciò che ci sta sopra: `--txt-dim` scende da 4,90:1 a
**4,30:1** (sotto la soglia WCAG di 4,5), `--cy-700` da 3,06:1 a **2,68:1**
(sotto 3). Sono rilievi aperti, dichiarati e non aggiustati di nascosto.

⚠️ **Costo reale.** Questa modifica riapre l'audit dei token su tutti i 18
componenti e impone un giro completo del ciclo §11.7. Non è un ritocco: è una
settimana. Va fatta per prima perché tutto il resto ne dipende.

I token sono entrati con le rev 5.8 e 5.9; **i componenti no**, ed è
deliberato: tararli contro un audit che non sapeva ancora giudicarli avrebbe
prodotto lavoro da rifare.

---

## 2. Densità di riempimento — 4,5 % contro 42 % · IMPATTO MASSIMO

**Riferimento visivo**: `famiglia-a/01`, calendario centrale — ogni cella è
**piena**, `#4d6d78` per la griglia e `#61868f` per l'evidenza ·
`famiglia-a/05`, colonna `MARKET DATA` con righe alternate su fondo pieno.

### La prova

Nel riferimento il pannello `BUSINESS` è un **blocco pieno** `#336276`, le celle
del calendario sono **piene** `#4d6d78`, il meteo è una banda **piena** `#13212a`.
Da noi ogni pannello è `--bg-panel` (L 18) con un bordo da 1 px.

### La correzione

Regole di riempimento, non un ritocco per pannello:

1. Ogni testata di pannello prende `--fill-1` come fondo, non solo un bordo sotto.
2. Ogni tabella e ogni lista alterna `--bg-panel` / `--bg-raised` per riga.
3. Ogni cella con uno stato — selezionata, attiva, sopra soglia — prende
   `--fill-1` o `--fill-2` come **fondo**, non come colore del testo.
4. Il pannello che ha il fuoco prende `--fill-1`; gli altri restano `--bg-panel`.
   Oggi il fuoco non si vede in nessun modo.
5. La tavola periodica: i quattro blocchi s/p/d/f oggi si distinguono per il
   colore del bordo. Nel riferimento si distinguerebbero per il **fondo**.

Criterio di accettazione, misurabile con lo stesso script che ha prodotto la
tabella §0: **pixel L>60 ≥ 25 %** su ogni workspace. Non 42 % — il riferimento
ospita fotografie e video, noi no — ma 4,5 % non è difendibile.

---

## 3. Il fondo troppo nero rende invisibili i bordi · IMPATTO ALTO

`--cy-900` (`#123840`, L 48) su `--bg-void` (`#070b0d`, L 10) dà un rapporto di
contrasto di **1,57:1** — misurato, vedi la correzione in fondo alla sezione. È
il bordo di **ogni** pannello della scrivania, ed è sotto la soglia in cui
l'occhio legge una linea come struttura invece che come rumore. Negli screenshot i pannelli si toccano senza che si veda dove finisce
uno e comincia l'altro.

**Correzione**: portare il bordo di cornice a `--cy-700` per il pannello col
fuoco. Misurato: **3,03:1**.

> ⚠️ **Correzione del 19 agosto 2026** (rev 5.8, `docs/acceptance/TOKENS-RIEMPIMENTO.md`).
> Questa sezione diceva «1,9:1» e prometteva che col fondo a `#0f1418` il
> rapporto sarebbe salito «a ~2,4:1». **Calcolati, i due numeri sono 1,57:1 e
> 1,47:1**: alzare il fondo lo AVVICINA al bordo, e il rapporto di contrasto
> `(L₁+0,05)/(L₂+0,05)` scende. Il fondo va alzato lo stesso — §1 lo motiva
> con la banda media, non col contrasto del bordo — ma il bordo dei pannelli,
> da solo, non si legge meglio: lo risolve `--cy-700`, oppure il fatto che il
> pannello smetta di essere un contorno e diventi una superficie (§2).

---

## 4. L'accento caldo è a zero · IMPATTO ALTO

**Riferimento visivo**: `famiglia-a/01`, colonna di cartelle a sinistra e
riquadro `CIRCA COMPANY` · `famiglia-a/05`, ticker `DOW JONES` in negativo su
fondo rosso — **un blocco solo**, ed è l'unico rosso della schermata.

§11.6 regola 2 dice «massimo 10 % della superficie colorata». È stata letta come
«evitare». Misura: riferimento **5,70 %**, WS01 **0,00 %**.

Nel riferimento il caldo non è solo l'allarme. È:

- le **cartelle manila** — una dozzina, in tre punti diversi dello schermo;
- il pannello `CIRCA COMPANY`, riempito di `#b48d64`;
- gli archi arancioni sulla mappa dei collegamenti;
- una sola cella rossa nel calendario — *quello* è l'allarme.

Da noi `--amber` esiste, è `#f0b06a` (L 185, praticamente lo stesso tono del
manila di riferimento) e compare solo come accento del workspace 04.

**Correzione**: `--manila` come colore di **contenitore** — cartelle nel file
manager, raggruppamenti nell'archivio, intestazioni di sezione. Resta separato
da `--amber` (avviso) e `--rust` (critico), così la semantica non si sporca.
Obiettivo misurato: pixel caldi fra **3 % e 6 %** per workspace.

---

## 5. Pannelli vuoti che occupano superficie · IMPATTO ALTO

**Riferimento visivo**: `famiglia-a/03-database-tabellare-denso.png` — è la
forma che deve prendere il file manager quando ha qualcosa da dire.

§11.6 regola 3 in vigore: *«se un pannello ha poco da dire, lo rimpicciolisca —
non lo riempia di spazio»*. Tre violazioni dichiarate:

| Dove | Cosa | Superficie sprecata |
|---|---|---|
| WS02 | File manager: **una riga**, `jf-tu3mtsr9` | ~40 % dello schermo |
| WS03 | Browser: `NESSUNA PAGINA APERTA` | ~45 % |
| WS03 | News: `NESSUNA NOTIZIA HA SUPERATO IL GATE` | ~28 % |

Lo stato vuoto è **corretto** — invariante 23 — ma un pannello vuoto grande come
mezzo schermo è la cosa che più fa sembrare finto l'insieme, più di qualunque
scelta cromatica.

**Correzione**, in ordine di preferenza:

1. **Dare contenuto vero.** `~/JARVIS` è vuoto: il file manager mostri la radice
   di progetto. Il browser apra una pagina di avvio reale. Il gate news lasci
   passare qualcosa al primo giro.
2. **Se non c'è contenuto, la cella si contrae.** Un pannello in stato vuoto
   dichiari una cella ridotta e la scrivania ricomponga il workspace.

La seconda è la regola generale e va scritta in `moduli.js`; la prima è ciò che
serve oggi.

---

## 6. ~~Manca la gerarchia di contenuto~~ — ❌ **IMPOSSIBILE, non rimandata**

> ### Chiusa il 24 agosto 2026
>
> **Le tre radici consentite contengono zero file immagine**, contati:
> `~/JARVIS` 0, `~/Documenti` 0, `~/Scaricati` 0. Non c'è media da mostrare.
>
> E la sonda dice che le **miniature dei nostri stessi scatti peggiorano**
> `dev.std` (30,0) e `L>60` (24,6 %): sono la nostra palette, copiarla non
> articola niente.
>
> Costruire il modulo significherebbe **inventare contenuto**, cioè violare
> l'invariante 23. Si riapre solo quando su quel disco ci sono immagini vere —
> e allora questa sezione è ancora giusta.
>
> *Testo originale sotto, per memoria.*

**Riferimento visivo**: `famiglia-a/01`, i quattro riproduttori più la webcam ·
`famiglia-a/05`, player grande con fascia sottotitolo piena e **griglia 8×2 di
miniature** in basso a sinistra · `famiglia-a/07-griglia-9up-con-web-incassato.png`
per la `<webview>`.

Nel riferimento ci sono **quattro riproduttori video, una webcam, miniature di
immagini, una filmstrip**. Materiale fotografico: pixel densi, ad alta
luminanza, con un bordo netto. È metà del peso visivo dell'immagine, ed è la
ragione per cui il 17 % dei pixel sta sopra L=120.

Noi abbiamo testo, SVG, tre.js e una `<webview>` che nessuno apre.

**Correzione**: un modulo *Media* nel WS03 che mostri anteprime reali —
gli screenshot in `shots/`, le immagini in `docs/design-reference/`, un video
YouTube nella `<webview>`. Il tool `web.py` esiste già, la `<webview>` è già
consentita da §6.3, e il pannello browser è già scritto. Manca chi lo alimenta.

---

## 7. Barra e dock sono strisce, non bande · IMPATTO MEDIO

> ⚠️ **Corretto il 19 agosto 2026 dopo la misura.** La prima stesura di questa
> sezione diceva «altezza raddoppiata». È **sbagliato**, e la misura lo mostra:
> la nostra barra è già più alta del riferimento. Il difetto è solo di
> riempimento.

**Riferimento visivo**: `famiglia-a/01` fascia 0–19px · `famiglia-a/05` fascia
0–15px · `famiglia-a/10` fascia 0–15px. Le tre concordano.

| | altezza | inchiostro (L>50) | luminanza media |
|---|---|---|---|
| `01-desktop-mcu-completo` | 3,4 % | **28,4 %** | 51 |
| `05-dashboard-news` | 3,3 % | **35,1 %** | 52 |
| `10-globo-gps-locator` | 3,3 % | **37,0 %** | 56 |
| **`shots/scrivania/ws-01`** | **4,3 %** | **2,8 %** | **19** |

**La nostra barra è già più alta e dieci volte più vuota.** Semmai va abbassata
al 3,3 %, non ingrandita.

Il dock sta allo stesso modo: riferimento `01` **26,2 %** di inchiostro, `05`
**22,8 %**, noi **2,8 %**. In `01` il dock è il doppio più alto della barra e
porta cinque icone grandi e geometriche, non pulsanti di testo.

**Correzione**:

1. Fondo `--fill-1` per entrambi, **pieno**, non un contorno su nero.
2. Riempirli con informazione **che già esiste e non mostriamo**: tool in
   allowlist, client collegati, uptime, byte sul socket, fase, PID, stato di
   ogni provider vocale, `seccomp`. Sono tutti in `state.snapshot` e oggi
   finiscono in un solo pannello.
3. Divisori verticali hairline fra i gruppi, non spazio vuoto.
4. In `10` la barra è su **due righe**: sigle sopra, valori sotto. È la forma
   che regge la densità maggiore senza rimpicciolire il corpo.
5. Il dock passa a icone geometriche monocrome; l'etichetta di testo resta come
   `title`, non come contenuto.

**Criterio**: inchiostro L>50 nella fascia della barra **≥ 25 %**, nel dock
**≥ 20 %**. Misurabile con `scripts/densita.mjs`.

## 8. ~~Mancano le colonne laterali persistenti~~ — ❌ **RIFIUTATA**

> ### Chiusa il 24 agosto 2026 — misurata e scartata, non rimandata
>
> `2e6d640`: **«NON ENTRA — è una somma.»** La colonna occuperebbe superficie
> che i pannelli usano già, e il dato che porterebbe — `fs.list` e
> `source.tree` — è oggi in due pannelli veri invece che in una fascia fissa.
>
> Va riaperta solo se la scrivania guadagna spazio, non prima.
>
> *Testo originale sotto, per memoria.*

**Riferimento visivo**: `famiglia-a/01`, alberi `FAVORITES`/`FOLDERS` e
`ELEMENTS` · `famiglia-a/10`, colonna `GPH_V02 COORDINATES` + `VOICE EQUALIZER` ·
`famiglia-a/05`, colonna del sito incassato con la sua barra di ricerca vera.

Il riferimento ha **due alberi permanenti** a sinistra (`FAVORITES`/`FOLDERS`,
`ELEMENTS`) e una colonna di filtri (`FILTER`/`COLLECTIONS`) al centro. Sono
sempre presenti, in ogni schermata della famiglia A, e sono ciò che dà
all'insieme l'aria di un sistema operativo invece che di un cruscotto.

**Correzione**: una colonna sinistra fissa larga 2 celle, presente in tutti e
quattro i workspace, con l'albero delle radici consentite. Il dato c'è già:
`fs.list` e `source.tree` sono pubblicati dal core e oggi alimentano un solo
pannello ciascuno.

---

## 9. Persistenza del layout — assente e non dichiarata · IMPATTO MEDIO

Non esiste `localStorage`, né alcun salvataggio. Sposta un pannello, riavvia,
torna alla cella dichiarata in `moduli.js`.

Non è nell'elenco dei «non verificato» di `SEZIONE-13.md` perché non è una
verifica mancata: è una funzione assente. Su un ambiente che resta aperto tutto
il giorno si nota al secondo riavvio.

**Correzione**: posizione, dimensione e stato acceso/spento per workspace,
salvati dal **core** — non dal renderer, che per invariante 1 non tocca il
disco. Un topic `ui.layout` in scrittura verso il core e un campo nello
snapshot al collegamento.

---

## 10. Risoluzione mai verificata fuori da 1536×839 · IMPATTO ALTO, COSTO NULLO

`SEZIONE-13.md` lo elenca come non verificato numero 4. È il più pericoloso dei
sei e costa cinque minuti: le celle scalano, le `min-width` dei pannelli no.

Lo strumento esiste già — è quello che ha dato «14 pannelli, 0 debordamenti».
Va rilanciato a tre dimensioni: la risoluzione vera della macchina, una più
stretta, e una 4K.

---

## 11. L'etichetta del budget news dice il contrario · IMPATTO BASSO, COSTO NULLO

`ui/src/panels/news.js` riga 238 calcola `BUDGET - usate` e scrive
`3/3 nell'ora`. Sono le interruzioni **rimaste**. Accanto a un pannello vuoto,
chiunque legge «tre usate su tre, per questo non c'è niente».

**Correzione**: `3 rimaste su 3`.

---

## 12. Il budget di frame misura l'intervallo, non il margine · IMPATTO BASSO

Mediana 16,70 ms = vsync. Dice «non perdo fotogrammi», ed è una buona notizia.
Non dice quanto delle 16,67 ms sia occupato: un renderer agganciato al vsync
mostra lo stesso numero che ne usi 4 o 16.

§10.4 pone il budget sul **lavoro** (three.js ≤8 ms, Pixi ≤3 ms, anime.js ≤4 ms).
Per conoscerlo serve il tempo per sottosistema con `performance.measure`, non
l'intervallo fra fotogrammi. Rilevante perché la misura attuale è stata presa a
scrivania ferma, per ammissione dell'autore.

---

## Cosa NON toccare

Elencato perché in una revisione così lunga il rischio è correggere ciò che
funziona.

- **La disciplina cromatica.** Saturazione 0,387 contro 0,349: allineata.
- **La tipografia.** Due famiglie, cinque corpi, ogni numero in monospace.
- **L'assenza di glow.** Verificata su tutti gli screenshot. È il confine con
  la Famiglia B e regge.
- **`border-radius: 0` e i tagli a 45°.** Coerenti ovunque.
- **L'anatomia a cinque parti.** Presente su tutti e 14 i pannelli.
- **I dati veri.** 118 elementi IUPAC, 312 fusi orari, ANSA reale, i fallimenti
  dichiarati invece che nascosti. È il pilastro del progetto.
- **L'audit dei token.** Va esteso ai nuovi ruoli, non indebolito.

---

## Ordine di lavoro

> ### Esito verificato il 24 agosto 2026 — **8 su 10, e due chiuse come impossibili**
>
> Quadro completo in `docs/STATO-DEI-PIANI.md`.

| # | Intervento | Costo | Esito |
|---|---|---|---|
| 1 | §10 risoluzioni · §11 etichetta news | 30 min | ✅ |
| 2 | §1 token di riempimento + fondo a `#0f1418` | 1 g | ✅ rev 5.9 |
| 3 | ~~§2 regole di riempimento su **18 componenti**~~ | ~~4–5 g~~ | ⚠️ **SUPERATA — i componenti a schermo sono SEI**, misurato in `d3d8978` |
| 4 | §5 pannelli vuoti — cella che si contrae | 1 g | ✅ `4a273ca` |
| 5 | §4 `--manila` come contenitore | 0,5 g | ✅ caldo 0 → **3,8 %**, nella forbice |
| 6 | §7 barra e dock come bande piene | 1 g | ✅ barra 63,7 % |
| 7 | ~~§8 colonna sinistra persistente~~ | ~~1,5 g~~ | ❌ **RIFIUTATA**, non rimandata: `2e6d640`, «non entra — è una somma» |
| 8 | ~~§6 modulo media~~ | ~~2 g~~ | ❌ **IMPOSSIBILE** — zero file immagine nelle radici, contati |
| 9 | §9 persistenza del layout | 1 g | ✅ `ui.layout` nel core |
| 10 | §12 strumentazione per sottosistema | 0,5 g | ✅ nucleo misurato anche **sotto carico** |

~~**Totale ~13 giorni.** I punti 2 e 3 valgono da soli l'80 % del divario.~~

> ⚠️ **Il punto 3 era la stima più cara del progetto, e il suo numero era
> sbagliato di tre volte.** «Diciotto componenti» contava il registro; a schermo
> nella scena di avvio ce ne sono **sei**. La mossa più redditizia fra i sei è
> stata misurata — l'emisfero illuminato del globo da `--fill-1` a `--fill-2` —
> e vale **+0,07 di entropia su +0,21 necessari**: un terzo, da un componente
> solo. *Quello* è il lavoro; il giro sui diciotto non lo è mai stato.
>
> Resta vero il metodo: un componente per volta, con lo screenshot **guardato**
> e la checklist §11.8 riportata. È quello che ha trovato il CSP di PixiJS, e
> funziona proprio perché è lento.

---

## Nota sul metodo

Le percentuali di §0 sono state calcolate su un fotogramma di film a 901×563 e
su screenshot a 1536×839. Compressione e scala influenzano i decimali, non gli
ordini di grandezza: 78 % contro 15 % non è un artefatto.

### ⚠️ E per la stessa ragione i BERSAGLI vanno in percentuale, mai in pixel

Aggiunto il 22 agosto 2026. Le metriche di §0 sono percentuali e attraversano
il confine senza danni; i **bersagli di dimensione** che questo documento e i
prompt hanno passato erano invece in pixel, e non lo attraversano:

```
Kx = 1536 / 901 = 1,705        Ky = 843 / 563 = 1,497
```

Due misure sono passate così e sono state costruite sbagliate:

- **«tessere 28×14 px»** — 28 px è l'**8,2 % della larghezza** del pannello
  catalogo del riferimento (342 px). Sul nostro, largo 605, la tessera vale
  **50×33**. È stata costruita 20×20: il numero dimezzato *e* il rapporto 2:1
  perso.
- **«icone del plinto 40 px»** — è il **4,4 % della larghezza** dell'immagine.
  Sui nostri 1536 sono **68 px**. Sono state costruite a 32.

Non è un dettaglio di rifinitura: sono proprio le due misure che questo
documento indica come «la differenza singola più grande» fra noi e il
riferimento, e le abbiamo trasferite dimezzate.

**Regola.** Un numero preso dal riferimento si scrive sempre accanto al proprio
denominatore — «il 4,4 % della larghezza», non «40 px». Un numero senza
denominatore è un numero che il prossimo trasferimento sbaglierà di nuovo.

Lo script che le produce è **`scripts/densita.mjs`**, ed è un criterio
eseguibile: esce con codice 1 quando una soglia non è raggiunta, così che
«densità» smetta di essere un'opinione e diventi qualcosa che il ciclo §11.7
può bocciare senza che nessuno debba leggere una frase.

```bash
node scripts/densita.mjs shots/scrivania/ws-01.png
node scripts/densita.mjs shots/globe.png \
     docs/design-reference/famiglia-a/10-globo-gps-locator.png
```

Usa Playwright per decodificare i PNG — già fra le devDependencies per il ciclo
§11.7 — quindi **nessuna dipendenza nuova**, come vuole `CLAUDE.md`.

Le soglie e il «cosa guardare» per ogni immagine di riferimento stanno in
`docs/design-reference/README.md`, sezione «COSA GUARDARE».
