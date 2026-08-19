# Divario verso il riferimento — analisi misurata

**Data**: 19 agosto 2026 · **Base**: commit `feat(§13): la scrivania`
**Confronto**: `docs/design-reference/famiglia-a/01-desktop-mcu-completo.png`
contro `shots/scrivania/ws-01..04.png`

Questo documento non contiene opinioni sul gusto. Contiene misure fatte sui
pixel dei due lati del confronto, e per ogni scarto una correzione dichiarata.

---

## 0. La misura che riassume tutto

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

## 6. Manca la gerarchia di contenuto — testo e vettori soltanto · IMPATTO MEDIO

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

## 8. Mancano le colonne laterali persistenti · IMPATTO MEDIO

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

| # | Intervento | Costo | Effetto |
|---|---|---|---|
| 1 | §10 risoluzioni · §11 etichetta news | 30 min | rischio chiuso |
| 2 | §1 token di riempimento + fondo a `#0f1418` | 1 g | abilita tutto il resto |
| 3 | §2 regole di riempimento su 18 componenti + ciclo §11.7 | 4–5 g | **il salto visivo** |
| 4 | §5 pannelli vuoti — contenuto vero, poi cella che si contrae | 1 g | via l'aria di mockup |
| 5 | §4 `--manila` come contenitore | 0,5 g | il calore del riferimento |
| 6 | §7 barra e dock come bande piene | 1 g | aria di sistema operativo |
| 7 | §8 colonna sinistra persistente | 1,5 g | densità strutturale |
| 8 | §6 modulo media con contenuto reale | 2 g | il 17 % di pixel chiari |
| 9 | §9 persistenza del layout | 1 g | ergonomia quotidiana |
| 10 | §12 strumentazione per sottosistema | 0,5 g | il margine, non l'intervallo |

**Totale ~13 giorni.** I punti 2 e 3 valgono da soli l'80 % del divario
percepito: sono la differenza fra un wireframe e una plancia.

Il punto 3 è anche l'unico che non si può accorciare. Diciotto componenti, uno
per uno, con lo screenshot guardato e la checklist §11.8 riportata. È il metodo
che ha già trovato il CSP di PixiJS — funziona proprio perché è lento.

---

## Nota sul metodo

Le percentuali di §0 sono state calcolate su un fotogramma di film a 901×563 e
su screenshot a 1536×839. Compressione e scala influenzano i decimali, non gli
ordini di grandezza: 78 % contro 15 % non è un artefatto.

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
