# Token di riempimento — esito · rev 5.8, 5.9 e **5.10**

**Data**: 19 agosto 2026 · **Riferimento**: `docs/DIVARIO-PREMIUM.md` §1 e §2,
`docs/design-reference/README.md` «COSA GUARDARE»
**Test**: **476 + 216** verdi (erano 446 + 211) · **Precedente**: `TOOLS-CODE.md`

> ⚠️ **Tre passate.** La 5.8 ha aggiunto sei riempimenti *accanto* alle
> superfici: leva sbagliata, i numeri non si sono mossi. La 5.9 ha spostato le
> superfici di base e ne ha tenuti tre: i numeri si sono mossi, e ha rotto il
> contrasto del testo. La 5.10 ritara la tipografia e **cambia il metro**,
> perché il metro era diventato inutile. Il documento tiene tutte e tre: le
> prime due sono il motivo per cui la terza si sa che è giusta.

Questo passo tocca **solo i token, la specifica e l'audit**. I 18 componenti
non sono stati toccati: e' il passo dopo, ed e' il ciclo §11.7 per intero.
Tararli adesso vorrebbe dire tararli contro un audit che non sa ancora
giudicarli.

---

## 1 e 6. La misura, prima e dopo

Stessa procedura le due volte: `npm run scrivania` e `npm run shot` rifanno
gli scatti, `scripts/densita.mjs` li misura. Gli scatti del «prima» sono stati
**rigenerati**, non riusati: due misure che vengono da procedure diverse non
si affiancano.

| | lum media | L>25 | **L>60** | L>120 | caldo | barra |
|---|---|---|---|---|---|---|
| **soglia** (`README.md`) | — | — | **≥ 25 %** | — | 3–6 % | ≥ 25 % |
| **riferimento** `famiglia-a/01` | 68,7 | 78,1 % | **42,1 %** | 17,4 % | 5,7 % | 28,4 % |
| ws-01 · prima | 24,1 | 14 % | **4,5 %** | 1,3 % | 0 % | 2 % |
| ws-01 · **dopo** | 24,3 | 14 % | **4,5 %** | 1,3 % | 0 % | 2 % |
| ws-02 · prima | 20,3 | 5,9 % | **1,3 %** | 0,5 % | 0 % | 1,8 % |
| ws-02 · **dopo** | 20,4 | 5,9 % | **1,3 %** | 0,5 % | 0 % | 1,9 % |
| ws-03 · prima | 20,3 | 5,8 % | **1,5 %** | 0,9 % | 0,1 % | 1,7 % |
| ws-03 · **dopo** | 20,5 | 5,8 % | **1,5 %** | 0,9 % | 0,1 % | 1,7 % |
| ws-04 · prima | 22,4 | 7,7 % | **1,8 %** | 0,4 % | 0,3 % | 1,7 % |
| ws-04 · **dopo** | 22,5 | 7,7 % | **1,8 %** | 0,4 % | 0,3 % | 1,7 % |
| telemetry · prima | 11,9 | 1 % | **0,2 %** | 0,1 % | 0 % | 0 % |
| telemetry · **dopo** | **19,6** | 1 % | **0,2 %** | 0,1 % | 0 % | 0 % |
| periodic · prima | 15,0 | 2,1 % | **0,8 %** | 0,4 % | 0,2 % | 0 % |
| periodic · **dopo** | **21,1** | 2,1 % | **0,8 %** | 0,4 % | 0,2 % | 0 % |
| files · prima | 12,9 | 1,3 % | **0,6 %** | 0,4 % | 0,1 % | 0 % |
| files · **dopo** | **20,5** | 1,3 % | **0,6 %** | 0,4 % | 0,1 % | 0 % |

**Nessuna colonna di superficie si e' mossa. Nemmeno di un decimo.**

E' l'esito atteso, ed e' il punto di questo documento: sei token nuovi non
disegnano niente. Un ruolo esiste quando un componente lo usa. Il divario da
4,5 % a 25 % lo chiude il passo dopo, e questo passo serve solo a mettere sul
tavolo i colori con cui chiuderlo — e un audit capace di giudicarli.

### La sola cosa che si e' mossa, e perche' solo li'

La luminanza media dei tre componenti sale di **7,7 · 6,1 · 7,6** punti, quella
dei quattro workspace di **0,1–0,2**. Stesso cambiamento, due effetti diversi
di un fattore quaranta. Misurato invece che immaginato — colori dominanti di
ws-01, per area:

```
#0e1315  --bg-panel   71,2 %     ← e' QUESTO che si vede
#0a1014  --bg-deep     5,8 %
#131a1d  --bg-raised   2,8 %
#0f1418  --bg-void     2,4 %     ← e' questo che ho cambiato
```

Sulla scrivania il fondo e' quasi tutto coperto: il 71 % di cio' che si guarda
e' il **corpo dei pannelli**. In galleria il componente e' piccolo e la pagina
e' fondo nudo, quindi lo stesso token sposta la media di otto punti.

La leva della scrivania non e' `--bg-void`: e' `--bg-panel`, e la sposta il
punto 1 di §2 — «ogni testata di pannello prende `--fill-1` come fondo».

---

## 2. La 5.8: sei ruoli accanto alle superfici — **la leva sbagliata**

```css
--fill-1:#13212a; --fill-2:#1e2631; --fill-3:#32464f;   /* L 31 · 37 · 66  */
--fill-4:#336276; --fill-5:#4d6d78;                     /* L 89 · 103      */
--manila:#b48d64;                                       /* L 146 — cartelle */
```

Piu' `--bg-void` da `#070b0d` a `#0f1418`. Tutti valori misurati sul
riferimento — e non e' bastato, per la ragione che la misura qui sopra
dichiarava gia': **`--fill-1` (L 31) e `--fill-2` (L 37) erano duplicati di
`--bg-panel` e `--bg-raised` alla luminanza giusta.** Un token nuovo accanto a
una superficie che nessuno cambia non dipinge niente.

---

## ⚠️ Due rilievi che la misura ha aperto, e non erano previsti

### R79 — `DIVARIO-PREMIUM.md` §3 sbaglia il conto del contrasto

§3 dice, testualmente: *«col fondo a `#0f1418` il rapporto sale a ~2,4:1»*,
partendo da un dichiarato 1,9:1. **Calcolato col rapporto WCAG, non e' vero
in nessuna delle due meta':**

| `--cy-900` (`#123840`) contro il fondo | §3 dichiara | misurato |
|---|---|---|
| `#070b0d` — prima | 1,9:1 | **1,57:1** |
| `#0f1418` — dopo | ~2,4:1 | **1,47:1** |

Il rapporto di contrasto e' `(L₁+0,05)/(L₂+0,05)`. Alzare il piu' SCURO dei
due — il fondo — lo avvicina al bordo e **abbassa** il rapporto. §3 ha
ragionato come se il fondo fosse il termine chiaro.

Il bordo dei pannelli, dopo questo passo, e' **meno** leggibile di prima, non
piu'. La seconda meta' di §3 pero' regge, ed e' l'unica che risolve davvero:
`--cy-700` sulla cornice del pannello col fuoco misura **3,03:1**.

Ho aggiunto la correzione in `DIVARIO-PREMIUM.md` §3: quel documento guida i
prossimi 4-5 giorni di lavoro, e un numero sbagliato li' dentro manderebbe il
passo successivo a inseguire un contrasto che non arrivera'.

### R80 — il fondo ha superato la barra, il dock e il corpo dei pannelli

La scala, dopo:

```
--bg-deep    L 15   barra e dock      ← adesso PIU' SCURI del fondo
--bg-panel   L 18   corpo pannello    ← 1 punto sopra il fondo
--bg-void    L 19   scrivania
--bg-raised  L 25
--fill-1     L 31
```

Prima il corpo del pannello stava 8 punti sopra la scrivania; adesso ne sta
**uno**. Nello screenshot si vede: il pannello si distingue dal fondo **solo**
per il proprio bordo — e per R79 quel bordo e' pure un po' piu' debole.

Non e' un errore del valore: `#0f1418` e' il fondo misurato del riferimento,
dove la barra e' `#1a1f23` (L 30), cioe' **piu' chiara** del fondo. Il
riferimento ha l'ordine opposto al nostro, e questo passo ha alzato solo il
primo dei termini. La scala si ricompone quando i pannelli prendono `--fill-1`
(L 31, dodici punti sopra la scrivania) e la barra una fascia piena — che e'
§2 punto 1 e la riga «Barra superiore» di `README.md`.

**Fino ad allora la scrivania e' piu' piatta di prima.** Dichiarato qui perche'
il prossimo che guarda uno screenshot lo vedra', e deve sapere che e' uno
stato di transito e non una regressione da correggere all'indietro.

---

## 3. La specifica non diverge piu'

`fonts.css` dichiarava dalla Fase 0 che tokens.css «e' la copia verbatim di
SPEC §10.1 e non deve divergere di un byte». Era una promessa: **nessuno la
verificava.**

`tests/test_tokens.py` la verifica adesso, e confronta il **testo**, non i
valori estratti: i commenti di §10.1 dicono cose che il codice non dice — «SEMPRE
zero», «MAX 10% della superficie colorata», le luminanze accanto ai
riempimenti — e sono meta' del valore della sezione.

Il controllo: cambiando **un solo byte** in §10.1 (`#32464f` → `#32464e`) il
test cade, e cade da solo. Rimesso il byte, torna verde.

SPEC portata a **rev 5.8** con la riga negli emendamenti. Un secondo test
verifica che la revisione dichiarata in testa abbia una riga in quella tabella:
§10.1 non si tocca senza dire perche'.

> ⚠️ **La richiesta diceva «porta la rev a 5.3».** La 5.3 esiste dal 18 agosto
> (Fase 5, le tre librerie scartate) e la specifica era gia' alla **5.7**. Ho
> usato la 5.8, che e' la prossima libera.

---

## 4. L'audit esteso, e la prova che non e' stato indebolito

`categorizza()` in `tokens-source.js` non conosceva `--fill-*` ne' `--manila`:
il LIVELLO 1 legge il valore calcolato, e senza il token nella famiglia
«colore» il primo componente che avesse scritto `background: var(--fill-3)`
sarebbe risultato **fuori sistema per aver fatto la cosa giusta**.

Aggiungerli allarga l'insieme ammesso. Di quanto? Le due fixture rispondono
misurando, non dichiarando.

| fixture | livello 1 | livello 2 | atteso |
|---|---|---|---|
| `conforme` — sei fondi `var(--fill-*)` e `var(--manila)` | 0 | 0 | **pulita** |
| `non-conforme` — quella di Fase 0b | 3 | 22 | illuminata |
| `non-conforme-banda` — **nuova** | 3 | 4 | illuminata |

`non-conforme-banda` usa tre grigi **inventati** dentro la banda dei
riempimenti — L 50, L 76, L 95, cioe' negli intervalli fra un `--fill` e il
successivo — e tutti e tre cadono a **tutti e due** i livelli. L'ampliamento
vale sei colori, non una banda.

La quarta regola e' il caso che rende visibile perche' il livello 2 esiste:
`background: #32464f` **e'** esattamente `--fill-3`, battuto a mano. Il
livello 1 lo lascia passare — calcola a `rgb(50,70,79)`, che ora sta nella
palette — e solo la lettura della REGOLA vede il letterale. Il test asserisce
entrambe le cose: che il livello 1 **non** lo segnali (o segnalerebbe i
riempimenti leciti) e che il livello 2 **lo segnali**.

---

## Un difetto trovato dai test, ed era il mio

Il modulo della fixture non si caricava e l'audit restava appeso senza dire
niente. Causa: **due backtick dentro un commento CSS** — `var(--fill-3)` e un
nome di file citati fra apici inversi dentro il template literal, che lo
chiudono a meta'.

E' la quinta volta in questo progetto, ed e' anche il motivo per cui esiste
`test_nessun_backtick_dentro_i_fogli_di_stile`: ha detto file e riga in un
secondo. La lezione operativa e' l'ordine — il test di sorgente costa un
secondo, l'audit col browser ne costa trecento quando va in stallo. Prima il
primo.

---

## ❌ NON VERIFICATO

1. **Nessun componente usa i tre riempimenti di stato.** Le superfici di base
   sono cambiate e si vedono ovunque, ma `--fill-1..3` li mostra solo la
   fixture `conforme`, che li dipinge come campioni. Finche' non lo fa un
   componente vero, «cella attiva» e «pannello acceso» sono nomi in un
   commento. **E' il passo dopo, ed e' tutto il valore.**
1b. ~~**R81 aperto**~~ ✅ **CHIUSO** con la rev 5.10: i tre colori del testo
   ritarati e verificati, e i numeri atomici della tavola periodica si leggono.
   Resta **R81b**, sulla superficie piu' chiara.
2. **Le luminanze del riferimento le ho prese da §1, non rimisurate.** I sei
   valori vengono dalla tabella dei colori dominanti di `famiglia-a/01`; ho
   verificato la luminanza dei valori **nostri**, non che quei colori siano
   davvero i dominanti di quell'immagine.
3. **La soglia «L>60 ≥ 25 %» non e' stata provata raggiungibile.** E' derivata
   dal riferimento, che ospita fotografie e video mentre noi no. Che sia
   raggiungibile con solo superfici piatte lo dira' il passo dopo — e se non
   lo fosse, e' la soglia che va rivista, non i componenti.
4. **`--manila` non ha ancora un uso deciso.** §4 lo destina a cartelle e
   contenitori; nessun componente ne ha. Sta nei token perche' viene dalla
   stessa misura degli altri, ma e' l'unico che potrebbe restare inutilizzato.
5. **Non ho affiancato i nostri scatti al riferimento a schermo.** Ho misurato
   e ho guardato i nostri; il giudizio «somiglia / non somiglia» resta di chi
   li mette uno accanto all'altro.
5b. **Nessuna misura di leggibilita' vera.** Il contrasto WCAG e' un modello,
   non un occhio: che i numeri atomici prima non si leggessero e adesso si
   leggano l'ho visto io, in due screenshot. Che 4,53:1 sia abbastanza per
   `--txt-dim` a corpo 11px, su questo pannello e con questi font, non l'ha
   misurato nessuno — e «l'ho guardato e mi sembra a posto» e' esattamente il
   tipo di giudizio che `densita.mjs` esiste per sostituire.
6b. **L'entropia non sa dove sta l'articolazione.** Misura l'istogramma, che e'
   cieco alla posizione: una scacchiera e una schermata divisa a meta' hanno
   la stessa entropia. Regge come soglia minima — sotto 1,3 bit non c'e'
   articolazione da nessuna parte — ma non distingue una plancia ben
   composta da un disordine ben distribuito.
7. **Le soglie non sono state provate raggiungibili DA NOI.** Che
   `famiglia-a/05` faccia 2,85 bit non dice che una scrivania di pannelli
   piatti possa farne 2,40. Se il passo dei componenti si fermasse a 2,0,
   sarebbe da capire se e' il lavoro a mancare o la soglia a essere sbagliata,
   e oggi non ho modo di dirlo.
6. **L'audit non guarda le SUPERFICI.** Continua a giudicare se un colore
   viene da un token, non se quel colore riempie qualcosa. La densita' la
   misura `densita.mjs`, su uno screenshot, fuori dai test: non c'e' niente
   che faccia cadere una build perche' un pannello e' vuoto.


---

# La 5.9 — spostare le superfici, non affiancarle

R80 non era uno stato di transito: era il segnale che la 5.8 era incompleta.

## La correzione

| | prima (5.8) | **dopo (5.9)** | ruolo |
|---|---|---|---|
| `--bg-void` | `#0f1418` L 19 | `#0f1418` L 19 | pavimento — invariato |
| `--bg-deep` | `#0a1014` L 15 | **`#1a1f23` L 30** | barra e dock |
| `--bg-panel` | `#0e1315` L 18 | **`#13212a` L 31** | corpo del pannello — il 71 % dei pixel |
| `--bg-raised` | `#131a1d` L 25 | **`#1e2631` L 37** | rilievo, riga alternata |
| `--fill-1` | `#13212a` L 31 | **`#32464f` L 66** | cella attiva, intestazione |
| `--fill-2` | `#1e2631` L 37 | **`#336276` L 89** | pannello acceso, selezione |
| `--fill-3` | `#32464f` L 66 | **`#4d6d78` L 103** | evidenza in griglia densa |
| `--fill-4`, `--fill-5` | L 89, L 103 | **eliminati** | erano il 2 e il 3 |
| `--manila` | `#b48d64` L 146 | invariato | cartelle |

**Tre registri, non una rampa.** Il riferimento non ha una scala monotona: ha
un pavimento (19), una banda di superficie (30–37) e riempimenti di stato
(66–146). Barra e pannello stanno nella **stessa** banda, e la barra si
distingue per densita' d'inchiostro — non per il fondo. Scritto nel commento
di §10.1 e imposto da due test, perche' un lettore che vede `--bg-deep` (30)
quasi uguale a `--bg-panel` (31) e' tentato di "sistemare" la rampa, e
distruggerebbe la cosa misurata.

## 1. La misura, adesso i numeri si muovono

Le due righe di ogni coppia vengono dalla **stessa** sessione di rendering:
scala del display identica, stessa procedura. Ho riscattato il «prima» coi
token della 5.8 rimessi apposta, perche' le prime misure erano a 2048×1115 e
queste a 1536×827 — stessa composizione, diversa densita' di pixel — e due
tabelle a fattori di scala diversi non si affiancano.

| | lum media | L>25 | **L>60** | L>120 | caldo | barra |
|---|---|---|---|---|---|---|
| **soglia** | — | — | **≥ 25 %** | — | 3–6 % | ≥ 25 % |
| **riferimento** | 68,7 | 78,1 % | **42,1 %** | 17,4 % | 5,7 % | 28,4 % |
| ws-01 · 5.8 | 25,0 | 16,4 % | **4,7 %** | 1,5 % | 0 % | 3,3 % |
| ws-01 · **5.9** | **36,2** | **96,9 %** | **5,5 %** | 1,8 % | 0 % | 4,5 % |
| ws-02 · 5.8 | 21,9 | 9,7 % | **2,0 %** | 0,9 % | 0 % | 3,2 % |
| ws-02 · **5.9** | **33,7** | **97,8 %** | **2,3 %** | 1,0 % | 0 % | 4,4 % |
| ws-03 · 5.8 | 20,8 | 7,7 % | **1,5 %** | 0,8 % | 0,1 % | 2,9 % |
| ws-03 · **5.9** | **33,1** | **97,8 %** | **1,8 %** | 0,9 % | 0,1 % | 4,2 % |
| ws-04 · 5.8 | 23,5 | 11,6 % | **2,5 %** | 0,9 % | 0,5 % | 2,9 % |
| ws-04 · **5.9** | **35,2** | **98,3 %** | **2,9 %** | 0,9 % | 0,4 % | 4,2 % |
| telemetry · 5.8 | 19,6 | 1,0 % | **0,2 %** | 0,1 % | 0 % | — |
| telemetry · **5.9** | **21,3** | **14,6 %** | **0,2 %** | 0,1 % | 0 % | — |
| periodic · 5.8 | 21,1 | 2,1 % | **0,8 %** | 0,4 % | 0,2 % | — |
| periodic · **5.9** | **24,9** | **31,9 %** | **0,9 %** | 0,4 % | 0,1 % | — |
| files · 5.8 | 20,5 | 1,3 % | **0,6 %** | 0,4 % | 0,1 % | — |
| files · **5.9** | **22,2** | **14,6 %** | **0,7 %** | 0,4 % | 0,1 % | — |

**`L>25` passa da 16,4 % a 96,9 %** su ws-01, e da 7,7 % a 97,8 % sul workspace
piu' vuoto. Nessun componente e' stato toccato: si e' mosso perche' il 71 % dei
pixel ha cambiato luminanza da 18 a 31. La previsione era esatta, e il fatto
che si sia avverata e' la verifica che la diagnosi fosse giusta.

**`L>60` resta dov'era** — da 4,7 % a 5,5 %. I riempimenti di stato non li usa
ancora nessuno, ed e' esattamente cio' che deve fare il passo dopo. La soglia
di 25 % e' ancora tutta da conquistare.

⚠️ **Abbiamo superato il riferimento su `L>25` (96,9 % contro 78,1 %) e siamo
a un quinto su `L>60`.** Non e' una vittoria: vuol dire che adesso la
scrivania e' *tutta* grigio-scuro uniforme invece che *tutta* nera. La
differenza col riferimento non e' piu' «quanto e' accesa» ma «quanto e'
articolata», ed e' una domanda che `L>25` non sa fare.

## 2. La scala non e' piu' invertita — e lo dice un test

```
--bg-void    L 19   <
--bg-deep    L 30   <=
--bg-panel   L 31   <
--bg-raised  L 37
```

`test_la_scala_delle_superfici_NON_e_invertita` impone quell'ordine, e un
secondo test impone che barra e pannello restino **entro 4 punti** l'una
dall'altro. R80 e' caduta una volta e ricadrebbe: chi tocca una di quelle
quattro righe non ha modo di accorgersene guardando il file.

## 3. ⚠️ Il costo lo paga il testo — tre soglie WCAG attraversate

Contrasto `(L₁+0,05)/(L₂+0,05)` su luminanza **linearizzata**. Non e' la Rec.
709 su 0-255 che misura la superficie accesa: confonderle e' l'errore che ha
prodotto il numero sbagliato in `DIVARIO-PREMIUM.md` §3.

| | su `--bg-panel` L 18 | su `--bg-panel` **L 31** | soglia |
|---|---|---|---|
| `--txt-primary` | 15,25:1 | 13,39:1 | 4,5 ✅ |
| `--cy-500` | 10,18:1 | 8,94:1 | 4,5 ✅ |
| **`--txt-dim`** | 4,90:1 | **4,30:1** | 4,5 ❌ **attraversata** |
| **`--cy-700`** | 3,06:1 | **2,68:1** | 3,0 ❌ **attraversata** |
| `--txt-ghost` | 2,12:1 | **1,86:1** | 3,0 ❌ era gia' sotto |
| `--cy-900` (bordo) | 1,48:1 | **1,30:1** | — |

**Guardato, non solo calcolato.** Negli scatti rifatti:

- `periodic` — i **numeri atomici** sono `--txt-ghost`, e a 1,86:1 sono quasi
  invisibili: si vede che ci sono, non si legge quale sia il numero;
- `console` — la colonna degli **orari** e' `--txt-ghost` e si comporta uguale;
- `periodic`, `console` — la legenda e il piede tecnico sono `--txt-dim`:
  leggibili, ma tirati.

**Non li ho aggiustati.** Alzare `--txt-dim` e `--txt-ghost` e' una decisione
sulla tipografia che tocca tutti i 18 componenti, e questo passo ha per
premessa di non toccarli. Il rilievo resta aperto:

> **R81** — `--txt-dim`, `--txt-ghost` e `--cy-700` sono tarati su un fondo a
> L 18 che non esiste piu'. Vanno rimisurati contro L 31 **prima** che i
> componenti si taggano sopra, o si tarera' la tipografia contro un contrasto
> che il passo dopo cambierebbe di nuovo.

`TestIlContrastoDelTesto` mette un **pavimento** sotto questi numeri: non li
benedice, impedisce che scendano ancora senza che nessuno se ne accorga.


---

# La 5.10 — cambiare il metro, e ritarare il testo

## 1. `L>25` era satura, ed è stata ritirata dal giudizio

Alla 5.9 `L>25` era passata dal 16,4 % al **96,9 %**, sopra il riferimento
(78,1 %). Da lì non poteva più bocciare niente: la supera qualunque schermata
con un fondo sopra L 25, **compresa una schermata di un colore solo.**

Una metrica satura è peggio di nessuna metrica, perché passa sempre e sembra
una verifica. Resta **stampata** come contesto — dice quanto è alzato il
pavimento — e non concorre più al giudizio.

Al suo posto due misure che una superficie uniforme non può ingannare:

| | cosa chiede | soglia | provenienza |
|---|---|---|---|
| **deviazione standard** | quanto la luminanza si allontana dalla media | **≥ 32** | metà fra 20,6 (5.7) e 40,6 (`05`) |
| **entropia** a 16 bin | quanto i livelli sono distribuiti, in bit | **≥ 2,40** | metà fra 1,34 (5.7) e 2,85 (`05`) |

Sedici bin e non 256: a 256 il rumore di compressione e l'antialiasing
riempirebbero decine di bin da soli, e l'entropia misurerebbe la qualità del
PNG invece della composizione.

**L'implementazione è ancorata da un test.** `densita.mjs` deve riprodurre
`55,7 / 3,32` su `famiglia-a/01`, `41,9 / 3,05` su `10` e `40,6 / 2,85` su
`05`. Cambiare il numero di bin o passare a una luminanza gamma sposterebbe
tutto e renderebbe le soglie arbitrarie senza che nessuno se ne accorga.

## 2. La previsione, e la conferma da un terzo angolo

> «Previsione: SCENDE, perché hai spostato il 71 % dei pixel da un picco a 18
> a un picco a 31 — più chiari, ugualmente monotoni.»

| ws-01 | lum | **dev.std** | **entropia** | 25–120 | L>60 |
|---|---|---|---|---|---|
| rev 5.7 | 24,6 | 20,6 | **1,34** | 14,6 % | 4,6 % |
| rev 5.8 | 25,0 | 20,5 | 1,25 | 14,9 % | 4,6 % |
| rev 5.9 | **36,2** | **18,7** | **1,25** | **95,1 %** | 5,4 % |
| rev 5.10 | 36,5 | 19,1 | 1,29 | 95,1 % | 6,0 % |

**Confermata.** L'entropia scende (1,34 → 1,25) e con lei la deviazione
standard (20,6 → 18,7), mentre la luminanza media sale di dodici punti. Il
lavoro sui token ha alzato il pavimento e **non ha articolato niente** — e per
il metro nuovo la scrivania di oggi è leggermente *peggio* di quella con cui
il lavoro è cominciato.

Non è una brutta notizia: è la stessa diagnosi di §1 e §2 vista da un angolo
indipendente, ed è la conferma che il lavoro vero sono i componenti.

La 5.10 recupera qualcosa (1,25 → 1,29) solo perché il testo più chiaro
aggiunge livelli all'istogramma. Diciotto centesimi di bit su una soglia di
2,40: dice quanto poco possa fare la tipografia da sola.

## 3. Dove siamo, con tutte le misure

| | lum | **dev.std** | **entropia** | L>60 | L>120 | caldo | barra |
|---|---|---|---|---|---|---|---|
| **soglia** | — | **≥ 32** | **≥ 2,40** | **≥ 25 %** | — | 3–6 % | ≥ 25 % |
| `famiglia-a/01` | 68,7 | 55,7 | 3,32 | 42,1 % | 17,4 % | 5,7 % | 28,4 % |
| `famiglia-a/10` | 58,9 | 41,9 | 3,05 | 34,8 % | 11,4 % | 0,4 % | 37,0 % |
| `famiglia-a/05` | 45,7 | 40,6 | 2,85 | **24,0 %** | 7,0 % | 3,7 % | 35,1 % |
| ws-01 | 36,5 | 19,1 | 1,29 | 6,0 % | 1,8 % | 0,1 % | 6,0 % |
| ws-02 | 33,8 | 16,6 | 0,79 | 2,6 % | 1,0 % | 0 % | 5,9 % |
| ws-03 | 33,2 | 16,5 | 0,72 | 2,0 % | 0,9 % | 0,1 % | 5,8 % |
| ws-04 | 35,4 | 14,1 | 1,35 | 3,4 % | 1,0 % | 0,4 % | 5,9 % |
| periodic | 24,9 | 13,2 | 0,78 | 0,9 % | 0,4 % | 0,1 % | — |
| glyphs | 23,5 | 16,6 | 0,33 | 1,8 % | 1,0 % | 0 % | — |
| console | 22,5 | 12,2 | 0,50 | 0,7 % | 0,3 % | 0,1 % | — |
| files | 22,2 | 13,2 | 0,44 | 0,7 % | 0,4 % | 0,1 % | — |
| telemetry | 21,3 | 7,6 | 0,10 | 0,3 % | 0,1 % | 0 % | — |

Siamo a **metà** della soglia di deviazione standard e a **poco più di metà**
di quella di entropia. `telemetry` a 0,10 bit è quasi un colore solo.

### ⚠️ Trovato da un test: la soglia `L>60` non la raggiunge un riferimento su tre

`famiglia-a/05` misura **24,0 %** contro la nostra soglia di 25. La soglia
resta — l'ha fissata `README.md` partendo da `01` (42,1 %) e le altre due
immagini la superano — ma non è vero che «il riferimento la raggiunge»: la
raggiungono **due su tre**. Il test lo enuncia come proprietà: una soglia deve
bocciare noi *e* essere raggiunta da almeno un riferimento, o è un desiderio.

## 4. R81 chiuso — la tipografia ritarata, e guardata

Verificati prima di scriverli, col rapporto WCAG su luminanza **linearizzata**:

| | prima | dopo | su `--bg-panel` | soglia |
|---|---|---|---|---|
| `--txt-dim` | `#6d878d` | **`#708b91`** | 4,30 → **4,53:1** | 4,5 ✅ |
| `--cy-700` | `#1f6b78` | **`#227482`** | 2,68 → **3,04:1** | 3,0 ✅ |
| `--txt-ghost` | `#3c4d52` | **`#556e75`** | 1,86 → **3,03:1** | 3,0 ✅ |

**Il calcolo dice di sì, e l'occhio conferma.** Negli scatti rifatti:

- `periodic` — i **numeri atomici** si leggono uno per uno, da «1» a «118».
  Prima si vedeva che c'erano, non quale numero fossero.
- `console` — la **colonna degli orari** si legge. Prima si scioglieva nel
  fondo del pannello.

### ⚠️ Ma la gerarchia si è compressa, e va detto

| | L prima | L dopo |
|---|---|---|
| `--txt-primary` | 231 | 231 |
| `--txt-dim` | 130 | 134 |
| `--txt-ghost` | **74** | **105** |

Il salto fra `dim` e `ghost` passa da **56 punti a 29**: dimezzato. Nella
console la colonna degli orari ha quasi lo stesso peso visivo dei nomi dei
topic, e a separarli resta soprattutto la tinta — grigio contro ciano — non
più la luminosità.

È il prezzo di portare a 3:1 un token il cui *mestiere* era essere fioco. Non
è un difetto da correggere all'indietro: `--txt-ghost` illeggibile non era un
sussurro, era un'informazione buttata. Ma chi userà i tre livelli nel passo dei
componenti deve sapere che oggi ne ha due e mezzo.

> **R81b** — su `--bg-raised` (`#1e2631`, la superficie più chiara) i tre
> colori restano sotto soglia: `--txt-dim` 4,21:1, `--cy-700` 2,82:1,
> `--txt-ghost` 2,81:1. Si chiude decidendo se le righe alternate portano
> testo secondario, e quella è una decisione dei componenti.

---

## Riepilogo

| | |
|---|---|
| Test | **476 + 216** verdi (erano 446 + 211), **35** nuovi — 30 nella suite, 5 negli eval |
| Revisioni | **5.8** (leva sbagliata), **5.9** (correzione), **5.10** (metro e tipografia) |
| Token cambiati | 3 superfici spostate, **3** riempimenti di stato, `--manila` |
| Componenti toccati | **0** — deliberato, in tutte e due le passate |
| `L>25` su ws-01 | 16,4 % → **96,9 %** senza toccare un componente |
| `L>60` su ws-01 | 4,7 % → **5,5 %** — la soglia 25 % e' del passo dopo |
| Rilievi aperti dalla misura | **4** — R79 (§3 sbagliava il conto), R80 (chiuso dalla 5.9), R81 (chiuso dalla 5.10), **R81b** (aperto, sulla superficie piu' chiara) |
| Soglie WCAG attraversate e poi **riportate sopra** | **3** |
| Metriche ritirate perche' sature | **1** — `L>25`, al 96,9 % |
| Entropia della scrivania | 1,34 (5.7) → **1,29** (5.10), soglia 2,40 |
| Fixture nuove | **1**, e cade a tutti e due i livelli |
| Invarianti che erano promesse e ora sono controlli | **5** — tokens.css ≡ SPEC §10.1, l'ordine delle superfici, le soglie WCAG, l'implementazione della metrica, la forma di una soglia |
