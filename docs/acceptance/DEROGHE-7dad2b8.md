# Le quattro deroghe di `7dad2b8` — cancello di governance

> **Turno 0 di `docs/PIANO-CORE-E-DENSITA.md`. Zero codice.**
>
> Il commit `7dad2b8` ha dichiarato tre deroghe a invarianti e ha emendato
> §11.6 da cinque corpi a sei. Le ha dichiarate nel proprio messaggio, il che è
> meglio del silenzio — ma dichiarare non è chiedere, e un invariante emendato
> dentro un turno di implementazione smette di essere un invariante.
>
> Questo documento non decide niente. Mette in fila le quattro, dice per
> ciascuna **che cosa si perde a non farla** e **quanto costa tornare
> indietro**, e lascia la decisione dove deve stare.

---

## Il risultato in una riga

**Tre delle quattro si sciolgono da sole entro il turno 3.** Solo la quarta —
il sesto corpo tipografico — sopravvive a tutto il piano ed è una decisione
vera, da prendere adesso.

| # | Deroga | La chiude | Decisione richiesta |
|---|---|---|---|
| 1 | invariante 25 — la nuvola gira sempre | **turno 3** (la nuvola cade) | no, se il turno 3 si fa |
| 2 | §25.5 — il nucleo arriva a L 255 | **turni 2 e 3** | no, ma con una verifica in più |
| 3 | §25.11 — testo nel nucleo | **già decisa dal proprietario**, §25.13 | no |
| 4 | §11.6 — sei corpi invece di cinque | **nessun turno** | **sì, e solo questa** |

---

## Deroga 1 — invariante 25: «zero animazione ambientale»

**Che cosa dice l'invariante.** *«Nessuna animazione senza causa. Zero
animazione ambientale.»*

**Che cosa fa il codice.** `ui/src/desk/sfondo.js` incrementa `giro` a ogni
fotogramma, senza che sia successo nulla. La velocità è un parametro di stato,
non un interruttore: la nuvola **non ha uno stato fermo**. Costa **4,49 ms per
fotogramma a riposo**, contro gli 0,15 della scrivania senza di lei — il 27 %
di un fotogramma a 60 Hz, per sempre, contro i 15 ms che l'invariante 26
assegna in tutto a tre motori.

**Perché l'ho fatta.** Perché il file veniva così dal mockup di famiglia-d, e
il proprietario aveva scelto di sostituire `presenza.js` con `sfondo.js`
sapendo il costo. La scelta era informata; la deroga però non è stata chiesta,
è stata dichiarata a cose fatte.

**Che cosa si perde a NON farla.** Niente. La nuvola è l'unica cosa che la
richiede, e il turno 3 la toglie: la geometria di `rings.js` nasce con
`autoplay: false` e si muove solo su `aggiorna({attivo: true})`, cioè su un
nodo attivo in `agent.mesh`. **Se gira, sta lavorando** — che è l'invariante 25
letto nel verso giusto.

**Costo del ritorno.** Zero: è il turno 3, che si fa comunque.

⚠️ **Una condizione, però.** Il turno 3 deve portarsi dietro anche il
`autoplay: false`. Se la fusione mantenesse la rotazione continua applicandola
agli anelli invece che ai punti, avremmo speso un turno per cambiare geometria
e tenuto il difetto.

---

## Deroga 2 — §25.5: la scala di luminanza del nucleo

**Che cosa dice la sezione.** Tratto del nucleo a riposo **L ≤ 48**; anello
attivo **`--cy-700`**; mai `--cy-500` né `--cy-100`.

**Che cosa misura il codice.** Sui pixel dell'insegna che arrivano a schermo:
**massima L 255**, media 36,9; il **15,4 %** oltre L 48 e il **5,0 %** oltre
L 92. I tetti sono assoluti, e sono superati.

**Da dove viene il superamento.** Da due sorgenti diverse, e vanno separate:

1. **il marchio** a `--icona-viva` (L 219), `desk/sfondo.js:177`. Da solo
   spiega il massimo a 255, perché lo scudo `text-shadow` lo isola dal fondo;
2. **la somma additiva della nuvola**: `globalCompositeOperation = "lighter"`
   accumula, quindi due punti tenui sovrapposti superano il tetto anche se
   nessuno dei due lo supera da solo.

**Che cosa si perde a NON farla.** Il primo pezzo: niente — il turno 2 porta il
marchio a `--cy-700` (L 100) come §25.13 regola 4 già prescrive. Il secondo
pezzo: niente — il turno 3 toglie la somma additiva insieme alla nuvola.

**Costo del ritorno.** Turno 2 = una riga. Turno 3 = la fusione, che si fa
comunque.

⚠️ **Ciò che resta da verificare dopo il turno 3.** La geometria di `rings.js`
dichiara il proprio tratto a `--cy-500` (L 181): come **pannello** deve farlo,
è un dato. Nello strato di presenza il tratto era riportato a `--cy-900` da una
regola di scope in `presenza.js`, **che non esiste più**. La fusione deve
riportarsi dietro quella regola, o la deroga 2 rientra dalla finestra.

---

## Deroga 3 — §25.11: «nessun testo nel nucleo coi pannelli aperti»

**Già decisa, e non da me.** Il proprietario ha emendato §25.11 il 22 agosto e
ha scritto **§25.13**, con sette regole e un criterio di accettazione. La
motivazione è nel documento: *«Un marchio non è un dato»*, e
`famiglia-a/12-logo-anelli-concentrici.png` — il riferimento che §25.1 assegna
a questo stesso componente — porta la scritta al centro con un filetto sotto.

**Non c'è niente da decidere.** Restano due cose da **fare**, che stanno nel
turno 2 e non in questo cancello:

- il colore: `--icona-viva` → `--cy-700` (§25.13 regola 4);
- **l'eccezione nominata nell'audit** per il corpo di `.sfd__marchio`, che
  §25.13.3 pretende e che oggi **non esiste**: `grep` su `scripts/audit.mjs` e
  `ui/src/gallery/audit.js` non trova nessun `marchio`. Finché non c'è, la
  deroga tipografica del marchio è tollerata da un audit che semplicemente non
  guarda quel componente.

---

## Deroga 4 — §11.6: sei corpi invece di cinque

**È l'unica che sopravvive al piano, ed è l'unica che chiede una decisione.**

**Che cosa dice la regola.** §11.6 regola 1 fissa cinque corpi — 8,5 / 11 / 12 /
14 / 20 — e la SPEC lo ripete tre volte, una delle quali è
`docs/SPEC.md:1359`: *«Due font, cinque corpi, nessuna deroga»*. «Nessuna
deroga» è scritto nella regola stessa.

**Che cosa ho fatto.** Aggiunto `--t-display: 48px` in `tokens.css`, cambiato
le tre occorrenze nella SPEC da «cinque» a «sei», e riscritto il test
`test_i_gradini_tipografici_sono_CINQUE` in `..._SONO_SEI`.

**La misura che lo motiva.** La lettura numerica di `famiglia-a/03` è alta
28 px su un'immagine larga 901: il **3,1 % della larghezza**, che sui nostri
1536 fa **48 px**. Il gradino più alto che avevamo, `--t-title` (20 px), nel
riferimento è il corpo dei numeri di **una cella del calendario**, non di una
lettura che occupa il pannello. Nessuno dei cinque ci arriva.

**Che cosa si perde a NON farla.** `panels/lettura.js` scende a `--t-title`, e
con lui la propria premessa: *«il numero È il pannello»* diventa «un pannello
con un numero dentro». La cifra passa dal 3,1 % della larghezza all'1,3 %. È
una perdita reale ma **circoscritta a un pannello che oggi non è nemmeno sulla
scrivania** (è uno dei quattro archetipi non montati).

**Costo del ritorno.** Piccolo e contato: `--t-display` ha **un solo
consumatore**, `ui/src/panels/lettura.js:113`. Tornare a cinque significa una
riga lì, togliere il token, rimettere «cinque» in tre punti della SPEC e nel
test. Mezz'ora.

### Le tre uscite, e che cosa costa ciascuna

| | Che cosa comporta | Costo |
|---|---|---|
| **A — si conferma il sesto gradino** | §11.6 passa a sei corpi. Il precedente esiste: la prossima misura che non entra nella scala avrà questo da citare | zero adesso, e un precedente |
| **B — si torna a cinque** | `lettura.js` a `--t-title`. Il pannello perde la propria ragione, e la misura del riferimento resta scritta ma non applicata | mezz'ora, e un archetipo indebolito |
| **C — sei corpi, ma il sesto è riservato** | `--t-display` resta con una regola accanto: **una sola dichiarazione in tutto il sistema**, imposta da un test che conta i consumatori | mezz'ora, e nessun precedente aperto |

**La mia raccomandazione è C**, e la ragione non è il compromesso: è che il
difetto vero della deroga 1 non era il numero, era che **un gradino nascosto
dentro un componente non si può contestare**. `calc(--t-title * 2.4)` faceva
esattamente 48 px e nessuno poteva discuterlo, perché per trovarlo bisognava
leggere quel file. Un token con un tetto di consumatori dichiarato risolve
entrambe le cose: si vede, e non si diffonde.

---

## Che cosa questo cancello NON copre

Deroghe e tensioni già dichiarate altrove, che restano aperte e non sono di
questo commit:

- **invariante 20** — i glifi PixiJS sono testo rasterizzato in WebGL, deroga
  dichiarata in `FASE-05.md:197-205`;
- **invariante 23** — `cpu 5.0 %`, `ram 30.3 %`, `temp 48.7 °C` in
  `docs/design-reference/famiglia-d/01-scrivania-viva.png` sono **inventati**
  (`MOCKUP-SCRIVANIA-VIVA.md:386`);
- **invariante 19, terza condizione** — «nessuna ombra su un elemento che non
  ne copre un altro» non è verificata (`ADR-010.md:317`), e lo scudo del
  marchio è esattamente quel caso: §25.13.4 lo dichiara ammesso, ma la regola
  generale resta non meccanizzata;
- **invariante 24** — il giro §11.7 sui 18 componenti (§26.10 punto 7) non è
  mai stato rifatto.
