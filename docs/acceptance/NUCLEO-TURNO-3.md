> ## 🔴 STORICO — il nucleo che questo documento misura NON ESISTE PIÙ
>
> Il 2 settembre 2026 il nucleo è stato rifatto sul riferimento «Aurora»: otto
> stati, tre gusci deformati da rumore FBM, catena di post-processing. Tutto
> quello che sta qui sotto — geometria, strati, criteri, numeri — misura un
> oggetto **cancellato**. Il codice sta in git e si recupera con un checkout.
>
> **Lo stato corrente è in `docs/acceptance/NUCLEO-AURORA.md`.**
>
> ⚠️ Questo documento **non si cancella** e non è un rifiuto: è il registro di
> ciò che è stato misurato e perché, ed è citato da 4 altri file. La
> «definizione di fatto» di CLAUDE.md poggia su questi referti. Serve però il
> cartello: fra il 24 e il 30 agosto un documento di stato ha detto il falso su
> cinque voci su cinque, **ed è stato creduto** — e la cura non è cancellare, è
> dire da quando una cosa non vale più.

# Turno 3 — la fusione dei due nuclei

> **`docs/PIANO-CORE-E-DENSITA.md`, turno 3.** La nuvola cade, entra la
> geometria di `rings.js`. Il marchio, le soglie di fase, l'onda e il contratto
> verso `app.js` restano.

---

## Il risultato in tre numeri

| | prima | dopo |
|---|---|---|
| pixel che cambiano in 250 ms **senza causa** | 5 568 (il 78 % del moto) | **0** |
| fotogrammi che l'insegna chiede in un secondo a riposo | ~60 | **0** |
| massimo del tratto nel ritaglio del marchio, senza il marchio | L 105,4 | **L 46,1** (§25.5 chiede ≤ 48) |

La terza riga chiude la seconda metà della **deroga 2** di
`DEROGHE-7dad2b8.md`: la somma additiva della nuvola superava il tetto di §25.5
da sola, e adesso non c'è più nulla che lo superi. La prima e la seconda
chiudono la **deroga 1**: non è che l'animazione ambientale sia stata spenta —
non esiste più il ciclo che la produceva.

---

## Che cosa è la fusione

Fino a oggi c'erano **due nuclei**: la nuvola di punti su canvas in
`desk/sfondo.js` e i cinque anelli SVG in `anim/rings.js`. Due implementazioni
della stessa idea di §25, che divergevano a ogni modifica di una delle due.

Adesso la geometria è **una**, e i montaggi sono due.

| dove | che cosa |
|---|---|
| `ui/src/anim/rings.js` | `costruisciDisco(svg)` — i cinque anelli, il gate di qualità, le animazioni **in pausa**, i raggi normalizzati. E `cssDisegno`, il foglio e i due pesi di tratto |
| `ui/src/anim/rings.js` | il pannello di §10.3 monta quella geometria dentro la propria cornice: è un **dato che si legge** |
| `ui/src/desk/sfondo.js` | l'insegna monta la stessa geometria dietro i pannelli: è **presenza** |

Le due differenze fra i montaggi sono dichiarate e sono due righe di CSS:
il pannello disegna a `--cy-500` (L 181), l'insegna a `--cy-900` (L 48,5),
perché §25.5 capa il tratto del nucleo a riposo a L ≤ 48.

---

## §25.6 alla lettera: una causa per anello

Non un cursore fra due estremi, non una tabella di stati inventata: ogni
anello ha la **propria** causa, e la causa è un fatto sul bus.

| anello | causa | verificato |
|---|---|---|
| 46 s | nodo `t1` attivo in `agent.mesh` | ✅ |
| 74 s | `voce.abilitata` e `voce.t1_vivo` — «in ascolto» | ✅ |
| 120 s | nodo `t2` attivo | ✅ |
| 233 s | un subagent attivo | ✅ ⚠️ lettura, non regola |
| ghiera fissa | nodo `t0` attivo — **un impulso, poi ferma** | ✅ |
| anello esterno | `--amber` sopra soglia §16, poi `--rust` | regola CSS, non esercitata |

⚠️ **L'anello 233 s è una lettura, non una regola.** §25.6 dice «T2 attivo →
anello 120 s in moto, **uno per slot**», e gli slot oltre il primo non hanno un
anello nominato. Gli si danno i subagent, che sono ciò che un T2 spawna. È la
lettura più vicina alla riga, ed è segnata come tale in `CAUSE`.

### Verificato nella finestra vera, non dedotto

`npm run verifica:scrivania` adesso esercita il nucleo, e il blocco esiste
perché **«gli anelli girano solo con una causa» non si vede in una schermata**:
una fotografia del nucleo fermo e una del nucleo in moto sono la stessa
immagine. L'unica differenza sta nel tempo.

```
aRiposo:                       []              nessun anello in moto
t1:  ["t1"]   ascolto: ["ascolto"]             una causa, l'anello suo
t2:  ["t2"]   subagent: ["subagent"]
t0:  []       impulsoChiedeFotogrammi: 17      un impulso, non un moto
              dopoLImpulsoSiFerma: 0
opacitaAFase3: [0.06, 0.06, 0.06, 1, 1]        i due interni accesi
opacitaAFase9: [1, 1, 1, 1, 1]                 tutti
fotogrammiInUnSecondoDiRiposo: 0               invariante 25, misurato
```

---

## I quattro difetti che solo la verifica ha trovato

Nessuno si vedeva leggendo il codice, e tre su quattro non si vedono in una
schermata.

| # | difetto | come si è visto | fatto |
|---|---|---|---|
| 1 | **`decidi()` sovrascriveva `forza()`**: due scrittori sullo stesso campo. `forza("ascolto")` durava un'istruzione, poi la voce del bus lo ricalcolava a `false` | `ascolto: []` — la causa forzata non muoveva niente | una variabile `forzato` che si vede, e i fatti del bus non scrivono mentre è alzata |
| 2 | **lo smorzamento non arrivava mai**: esponenziale con soglia di uscita a 0,002 | mezzo secondo dopo il salto a fase 9, tre anelli stavano a **0,85** invece che a 1, e il ciclo chiedeva fotogrammi per due secondi dopo ogni cambio | si aggancia al bersaglio sotto il centesimo: un valore esatto e un ciclo che finisce |
| 3 | **la misura del «si è fermato» contava la coda del fenomeno**: la finestra cominciava dentro l'impulso | rispondeva «6 fotogrammi» a qualunque durata di finestra — allungarla non li toglieva, erano già dentro | la finestra comincia quando il fenomeno è finito |
| 4 | **il centraggio**: `place-items: center` con due figli fa due righe | il disco sarebbe finito sopra il marchio invece che dietro | il disco si centra fuori dal flusso, con due traslazioni della metà del proprio lato |

E un quinto, che è di una misura già committata: vedi la correzione qui sotto.

---

## ⚠️ La correzione alla misura del turno 1

Guardando lo scatto della scrivania si vede una **cartella manila**. La misura
di occlusione del turno 1 contava **zero** elementi caldi fuori dai pannelli.

La causa: il predicato guardava `background-color` e, per chi ha testo proprio,
`color`. Un glifo SVG non ha né l'uno né l'altro — `segni.js` lo dipinge con
`fill="currentColor"`, apposta, perché un segno non ha un colore proprio ma
quello del posto in cui sta. Aggiunto il terzo modo di dipingere, la misura
risponde **1 elemento caldo sul pavimento, 0 coperti**.

La conclusione del turno 1 regge — quell'unico elemento è il glifo 32×32
dell'icona residua, lo **0,085 % del pavimento**, e il caldo continua a non
essere nascosto sotto i pannelli — ma **il numero era sbagliato, e un buco che
dice «zero» conferma qualunque tesi**. `OCCLUSIONE-TURNO-1.md` porta la
correzione datata.

È anche la ragione per cui §11.7 mette lo sguardo **dopo** la misura e non al
posto suo: né la misura né l'occhio, da soli, avrebbero trovato questo.

---

## ⚠️ La deroga: il diametro non è quello di §25.7

§25.7 chiede **«diametro = 64 % dell'altezza dell'area pannelli»**, cioè Ø502
sulla finestra di misura. **Non ci entra.**

Il buco che la scena `avvio` lascia libero fra i quattro pannelli è **Ø344** —
misurato, non stimato: `scripts/occlusione-dom.js` cerca il raggio massimo
attorno al centro che nessun pannello tocca. A Ø502 il nucleo sarebbe coperto,
che è esattamente la cosa che il centro libero era stato scelto per evitare.

Il nucleo resta all'ampiezza misurata dell'insegna, **Ø326**: sta nel buco con
il 90 % di riempimento e risulta coperto allo **0,0 %**.

**§25.7 non è emendata**, e non lo è di proposito: le regole di uscita del piano
(§6) vietano di emendare una regola dentro un turno di implementazione. La
decisione sul diametro è stata presa dal proprietario il 23 agosto 2026, fra tre
uscite e con i numeri davanti; la sezione va allineata in un turno di
governance, non qui.

Il seguito di quella decisione, e va scritto perché non si riscopra: **§25.5
capa il tratto a L ≤ 48 e la densità conta sopra L 60**, quindi il nucleo — a
qualunque diametro — **non contribuisce alla densità**. Misurato: `L>60` è 9,3 %
prima della fusione e 9,2 % dopo. È la tensione 1 di Parte 3 del piano, e resta
aperta per scelta dichiarata.

---

## Che cosa si è perso con la nuvola

Va scritto perché erano tre idee giuste, per un oggetto che non esiste più:

- **la bassa discrepanza ad angolo d'oro** — ogni punto nel varco più largo
  lasciato dai precedenti, uniforme come una griglia senza esserlo;
- **il profilo radiale misurato su nove ripiani**, dove la luminanza della banda
  diventava densità di punti invece che chiarezza;
- **la somma additiva**, per cui il centro di una banda era chiaro perché i
  punti si sovrapponevano;
- **il dito**, che apriva la nuvola solo sul vuoto della scrivania.

La misura che le motivava è `famiglia-a/12-logo-anelli-concentrici.png`, che
§25.1 assegna a questo componente: descrive un **logo di anelli concentrici**.
La nuvola era una lettura di quel riferimento; gli anelli sono il riferimento.

---

## Le misure, protocollo §5

Finestra 1536×843 massimizzata, scena `avvio`, quattro pannelli, T+3 s, passo
2 px, mediana di due scatti.

```
mediana   lum 34.5 · dev 20.1 · H 1.57 · 25-120 61.8% · L>60 9.2% · L>120 1.0%
          caldo 0.2% · barra 63.3%

pavimento coperto dai pannelli 56.5 % · cornice 7.1 % · libero 36.5 %
caldi     0/1 coperti          icone 0/1 coperte
nucleo    disco Ø326 = 6.93 % del pavimento · coperto 0.0 % · libero 100.0 %
il buco   Ø344 = 7.73 % del pavimento, il nucleo ne occupa il 90 %
marchio   luminanza media 25.3 · contrasto 3.40:1 — §25.13.5 SODDISFATTO
```

Il moto residuo è **telemetry 91 %, altrove 9 %**: pannelli che ricevono dati.
Su quattro esecuzioni il nucleo non compare mai.

Suite: **561 passed** (557 più i quattro di `tests/test_nucleo.py`).
Audit `rings`: 0 violazioni calcolate, 0 sorgente.

---

## Che cosa NON è stato verificato

- **L'accento caldo dell'anello esterno** (`--amber` su `warn`, `--rust` su
  `critical`) è una regola CSS che nessuna esecuzione ha esercitato: il livello
  è restato `nominal` per tutta la verifica. La regola c'è, il pixel no.
- **L'onda** — il guscio che viaggia dal mozzo al bordo su cambio di mesh — è
  esercitata solo indirettamente, dall'impulso di `t0`. Nessuna misura la
  guarda come guscio.
- **Il costo per fotogramma in millisecondi** non è stato misurato: a riposo il
  componente non chiede fotogrammi, quindi il numero da confrontare con i
  10,36 ms della nuvola **non esiste** — non è zero per approssimazione, è che
  non c'è un ciclo. Il budget §10.4 sull'insieme resta mediana 16,7 ms, cioè
  sul vsync, che non sa distinguere le due stesure.
- **`ui/src/desk/sfondo.js` non passa da `scripts/audit.mjs`**: non è
  registrato in galleria. Vale per lui la stessa lacuna già segnalata nel
  turno 2.

### Due difetti PREESISTENTI che la verifica mostra, e che non sono di questo turno

`npm run verifica:scrivania` esce **1**, e usciva 1 anche prima: `git diff`
contro il turno 2 su `moduli.js`, `app.css` e `cornice.js` è vuoto.

1. **`dock.length === 8`, misurato 9.** L'asserzione è vecchia: i moduli sono
   cresciuti e nessuno l'ha aggiornata.
2. **La cornice col fuoco è identica a quella senza**: entrambe
   `rgb(205, 238, 243)` = `--cy-100`, dove `app.css` prescrive `--cy-500` sul
   pannello a fuoco. O la classe `.focus` non arriva, o la misura legge
   l'elemento sbagliato.

Il secondo è un difetto vero di §26 e va aperto per conto suo. Che siano
rimasti rossi finché qualcuno non è andato a leggere il codice di uscita —
invece dei numeri del budget che quel comando stampa — è il difetto sopra il
difetto.
