# Il fondo pieno alle tabelle — e l'entropia passa per la prima volta

**Rollback:** `b769369`
**Criteri:** entropia ≥ 2,40 bit · `L>60` ≥ 25 %
**Esito: SODDISFATTI ENTRAMBI. Entropia 2,4127. `L>60` 26,98 %.**

---

## 1. Che cosa dice il riferimento, misurato

`docs/design-reference/README.md`, nella sezione che fissa proprio la soglia
`L>60`:

> `05`, colonna `MARKET DATA`: righe alternate su fondo pieno, con il valore in
> monospace a destra. **È esattamente la forma che devono prendere le nostre
> tabelle.**

Il riferimento delle tabelle è `03-database-tabellare-denso.png`. Prendendo il
colore **dominante** di ogni fascia dell'elenco `IP ADDRESS BOOK` — non la
mediana, che la barra di scorrimento sporcava:

| fascia | riferimento | L | nostro token | L |
|---|---|---|---|---|
| chiara | `#286077` | 85,8 | `--fill-2` `#336276` | 89,5 |
| media | `#235266` | 73,5 | *nessuno* | — |
| scura | `#2c4758` | 66,5 | `--fill-1` `#32464f` | **66,4** |
| varco | `#132c40` | 40,1 | `--bg-raised` `#1e2631` | 37,1 |
| scelta | `#93714c` | 117,6 | `--manila` `#b48d64` | 146,3 |

**Due livelli su tre combaciano, e uno alla virgola.** Il livello di mezzo non
esiste nella nostra palette e si salta: il ciclo diventa a due.

## 2. Dove mancava il fondo, e dove c'era già

Contro l'aspettativa, due delle tre tabelle **ce l'avevano già**:

- `panels/files.js` — `background: var(--manila); color: var(--bg-void)`, righe
  separate da un filetto. È il modello del riferimento, fatto col manila che
  §26.5 riserva ai contenitori.
- `panels/cartella.js` — lo stesso.

Mancava dove il dato non è un file:

- **`panels/telemetry.js`**, i tre processi: la tabella di **dati** della
  scrivania;
- **`panels/tabella.js`**, la tabella generica.

Ed entrambe portavano la stessa ricetta, che si bocciava da sola nel proprio
commento:

> ② SEI PUNTI DI L, non un colore. `--bg-panel` su `--bg-raised` misura
> **1,08:1**: si vede che sono righe, non si vede la riga.

Una zebra a 1,08:1 non è una zebra. Restava scritta come se fosse una scelta.

## 3. Due ricette, e perché non è una duplicazione

**`tabella.js` — alternanza `--fill-1` / `--fill-2`.** 255 righe, nessuna barra:
la zebra serve a seguire una riga fra molte, ed è esattamente il caso del
riferimento.

**`telemetry.js` — tutte a `--fill-1`, nessuna alternanza.** Tre righe, e
ognuna porta la propria **quota di CPU disegnata**, che è `--fill-2`. Portare
una riga su due a `--fill-2` spegnerebbe la barra dentro il proprio fondo: il
dato sparirebbe. Il varco resta il filetto di `--bg-raised`, come in `files.js`.

Non sono due opinioni sulla stessa cosa: sono due situazioni diverse, e ognuna
lo dichiara puntando all'altra.

## 4. La perdita, dichiarata

Su una riga piena **`--txt-dim` non regge**:

| testo | su `--bg-raised` | su `--fill-1` | su `--fill-2` |
|---|---|---|---|
| `--txt-primary` | 12,43:1 | 8,06:1 | **5,44:1** |
| `--txt-dim` | 4,93:1 | **3,19:1** | **2,15:1** |
| `--txt-ghost` | 3,76:1 | 2,44:1 | 1,64:1 |

Il 4,5 che `tests/test_tokens.py` impone cade. E **nessun token della palette
lo recupera**: sotto `--txt-primary` il primo che regge è `--icona-viva`, con
4,80:1 su `--fill-2` — ma 219 contro 231 non è una gerarchia che si veda.

Quindi in `tabella.js` **tutto il testo di riga diventa primario**, e la
distinzione primario/secondario dentro la riga se ne va col fondo pieno. Il
commento che la difendeva — «in una tabella tutta a `--txt-dim` non si capisce
che cosa si sta guardando» — vale ancora, e non ha più un colore con cui
rispondere. È lo stesso conto della rev 5.10, quando alzare `--bg-panel` a L 31
attraversò tre soglie WCAG.

La riga **scelta** passa da `--fill-2` a `--manila` con testo `--bg-void`
(6,12:1): `--fill-2` adesso è il fondo di metà elenco, e dire «scelta» col
colore di metà elenco non direbbe niente. Il manila è un cambio di **tinta**,
che sopravvive all'alternanza — ed è quello che fa il riferimento.

## 5. La misura

| | prima | dopo |
|---|---|---|
| **entropia** | 2,3772 | **2,4127** ✅ |
| **`L>60`** | 24,64 % | **26,98 %** ✅ |
| dev.std | 34,0 | 34,06 |
| bin 0 | 4,3 % | 4,6 % |
| bin 4 | 13,7 % | 16,0 % |
| caldo | 3,8 % | 3,8 % |
| barra | 63,8 % | 63,8 % |

E l'attribuzione:

```
scrivania.png contro prima.png: 46.726 pixel (3,61 %), massimo scarto 180/255
  telemetry      40163
  altrove         6563
```

I 6 563 «altrove» sono le icone del pavimento: lo scatto di confronto è
anteriore alla luce che il turno precedente ha dato loro. Nient'altro si è
mosso.

**È la prima volta che l'entropia passa.** Era 2,2032 ieri mattina.

## 6. §11.8, punto per punto

```
GEOMETRIA
✓ border-radius 0 — non toccato
✓ tagli a 45° — non toccati
✓ spaziature — non toccate; il varco e' --line-hair, una LARGHEZZA DI LINEA
   usata come bordo e non come margine (l'audit l'ha bocciata 24 volte
   quando era un margine)
✓ pesi di linea hair/base/bold
COLORE
✓ tutti da tokens.css — audit di `tabella` e `telemetry` pulito, 0 letterali
✓ caldo 3,8 % < 10 %
✓ tinte ≤ 3 — fill-1 e fill-2 sono la stessa famiglia fredda, il manila e' la
   seconda, --icona dell'intestazione e' neutro
✓ zero gradienti — le righe sono tinte piatte
✓ ZERO alone, bloom, glow
✓ nessuna ombra aggiunta
TIPOGRAFIA
✓ i sei gradini — non toccati
✓ numeri in --font-mono con tabular-nums
CONTENUTO
✓ dati veri — 255 file veri nella galleria, i tre processi dal core
✓ etichetta + ID + piede tecnico presenti
✓ densita': entropia 2,4127 e L>60 26,98 %, entrambe SOPRA soglia
MOVIMENTO
✓ nessuna animazione aggiunta; l'hover e' un filtro, non una transizione nuova
TECNOLOGIA
✓ non toccata
```

Guardato: `shots/tabella.png` e `shots/telemetry.png`, più la scrivania intera.
Le righe alternate si leggono come fasce, la selezione manila stacca, e la
quota della CPU si stacca ancora dal fondo pieno — Δ23 punti di L contro
`--fill-2`, Δ37 contro `--fill-3`.

## 7. Verifica

| | |
|---|---|
| `npm run shot -- tabella` | audit 0 fuori sistema, 0 letterali · OK |
| `npm run shot -- telemetry` | audit 0 fuori sistema, 0 letterali · OK |
| `npm run scrivania:fixture` | EXIT=0, `scattiIdentici` true |
| `uv run pytest -q` | **585 passed** |

## 8. Dichiarato aperto

- **La gerarchia primario/secondario dentro la riga non c'è più**, e non è
  recuperabile con la palette attuale. Se la si rivuole serve un token di testo
  fra L 171 e L 219 che regga 4,5:1 su `--fill-2` — cioè una misura, non una
  scelta.
- **Il livello di mezzo del riferimento** (L 73,5) non esiste da noi: il ciclo è
  a due invece che a tre, quindi la nostra alternanza è un po' più marcata
  (Δ23,1 contro i Δ19,3 del riferimento).
- **Bin 14 e 15 restano a 0,00 %** contro 0,7 % e 1,9 %: nessuna superficie
  sopra L 224. Nel riferimento quella massa è contenuto fotografico.
- **Dock al 2,0 % contro 20.** In rapporto, non blocca. È il divario più grande
  che resta.
- Le misure valgono per la registrazione `4d5edf35cfdb64af` (§11.9).
