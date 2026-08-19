# Token di riempimento — esito · rev 5.8

**Data**: 19 agosto 2026 · **Riferimento**: `docs/DIVARIO-PREMIUM.md` §1 e §2,
`docs/design-reference/README.md` «COSA GUARDARE»
**Test**: 460 + 212 verdi (erano 446 + 211) · **Precedente**: `TOOLS-CODE.md`

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

## 2. I sei ruoli, e il fondo

```css
--fill-1:#13212a; --fill-2:#1e2631; --fill-3:#32464f;   /* L 31 · 37 · 66  */
--fill-4:#336276; --fill-5:#4d6d78;                     /* L 89 · 103      */
--manila:#b48d64;                                       /* L 146 — cartelle */
```

E `--bg-void` da `#070b0d` (L 10) a `#0f1418` (L 19). I valori sono quelli
misurati sul riferimento in §1, non scelti.

La scala verificata da un test: sale sempre, e ogni gradino dista almeno 5
punti dal precedente. Un ruolo che non si distingue dal precedente non e' un
ruolo, e cinque nomi su tre colori sarebbero peggio di tre nomi.

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

1. **Nessun componente usa i sei ruoli.** L'unica cosa che li mostra e' la
   fixture `conforme`, che li dipinge come campioni. Finche' non lo fa un
   componente vero, «riga alternata» e «cella attiva» sono nomi in un
   commento. **E' il passo dopo, ed e' tutto il valore.**
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
   stessa misura degli altri cinque, ma e' l'unico dei sei che potrebbe
   restare inutilizzato.
5. **R80 non e' stato provato a occhio contro il riferimento.** Ho misurato la
   scala e guardato lo screenshot; non ho affiancato i due a schermo per
   giudicare se la scrivania *sembri* piu' piatta o solo *misuri* piu' piatta.
6. **L'audit non guarda le SUPERFICI.** Continua a giudicare se un colore
   viene da un token, non se quel colore riempie qualcosa. La densita' la
   misura `densita.mjs`, su uno screenshot, fuori dai test: non c'e' niente
   che faccia cadere una build perche' un pannello e' vuoto.

---

## Riepilogo

| | |
|---|---|
| Test | **460 + 212** verdi (erano 446 + 211), **15** nuovi |
| Token aggiunti | **6** ruoli di riempimento, 1 fondo cambiato |
| Componenti toccati | **0** — deliberato |
| Colonne di superficie mosse dalla misura | **0 su 7** |
| Rilievi aperti dalla misura | **2** — R79 (§3 sbaglia il conto), R80 (la scala si e' invertita) |
| Fixture nuove | **1**, e cade a tutti e due i livelli |
| Invarianti che erano promesse e ora sono controlli | **1** — tokens.css ≡ SPEC §10.1 |
