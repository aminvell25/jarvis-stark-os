# I cinque rossi di `eval_visual.py` — e perché erano rossi da giorni

**Rollback:** `db25919`
**Richiesta:** «Sistema i cinque rossi di `eval_visual.py`».
**Esito: cinque su cinque verdi. Due erano difetti veri del codice, tre erano
test che dicevano il falso. E la ragione per cui nessuno se n'era accorto è
che quei file NON VENIVANO ESEGUITI: `python_files` non li raccoglieva, e con
loro restavano fuori 275 test.**

---

## 0. La causa comune

```toml
testpaths = ["tests"]
```

e nient'altro. Il predefinito di pytest raccoglie `test_*.py`; gli eval si
chiamano `eval_*.py`, e il corpus `t0_corpus.py`. **Non entravano mai.**

Il commento del marker, nello stesso file, diceva:

> Gli eval visivi che aprono un browser: secondi, non millisecondi. **Girano
> con tutto il resto**, e si possono escludere con `-m "not slow"`.

Non giravano con niente. §22 li chiama «l'unico modo di accorgersi che una
sessione ha rotto qualcosa che funzionava tre fasi fa» e dice di eseguirli
**all'inizio di ogni fase**: una suite che nessuno esegue non si accorge di
niente, e ci sono voluti giorni perché qualcuno guardasse.

Aggiunto `python_files`. La suite passa da **792 a 1067**: duecentosettantacinque
test che c'erano, erano scritti, e non venivano eseguiti — compresi i due eval
di ADR-007 scritti in questa stessa sessione, che credevo di aver visto girare
nella suite e invece giravano solo quando li invocavo per nome.

## 1. Due difetti veri del codice

### `cartella` era entrata nell'indice senza passare dalla riga

Il test dice, alla lettera, cosa sorveglia:

> ciò che si aggiunge dopo va aggiunto QUI insieme alla sezione che lo
> introduce. Un modulo che comparisse senza toccare questa riga sarebbe
> entrato nell'indice senza che nessuno lo abbia deciso.

`cartella` è nel dock dal commit `03276b3` e quella riga non è mai stata
toccata. **Il test aveva ragione**: aggiunta, con la sua sezione (§26.5).

### `cartella` si sovrapponeva a due pannelli della sua categoria

`[4,3,3,1]` copriva `file` in (4,3) e `archivio` in (5,3) e (6,3).

Non era una svista di posizionamento: la categoria 02 è **già piastrellata per
intero** — `file`, `sorgente` e `archivio` fanno 48 celle su 48, misurate —
quindi qualunque posto le si desse sarebbe stato sopra qualcosa. Il commit che
la introduce lo dice nel titolo: *«e il posto non c'è»*.

Il meccanismo giusto esisteva già e il test lo documenta: `fuoriPiastrellatura`,
per i moduli aggiunti **dopo** §13, che non hanno un quarto di griglia da
riempire. `meteo` lo dichiara; `cartella` no. Dichiarato. Verificato: senza di
lei la categoria 02 torna a 0 sovrapposizioni e 0 buchi.

## 2. Tre test che dicevano il falso

### `--cy-500` non è più vietato — e la SPEC lo aveva già scritto

§25.5 è stata emendata il **23 agosto**: l'anello attivo può stare a `--cy-500`
a **una condizione — uno per volta**. La SPEC §25.13 lo dice del test stesso:

> ~~nessun tratto usa `--cy-500`~~ — **oggi direbbe il falso** […] Il test in
> vigore verifica il divieto di `--cy-100` e **conta gli anelli accesi
> insieme**, che è la condizione vera.

Il test era rosso da due giorni contro un codice conforme, e la sostituzione
era già scritta. Fatta — e la condizione si conta su una **misura viva**, non
sul sorgente: `app/main.js --marchio-stati` aziona `fissa(stato)` nella
finestra vera per nove stati, e `fissa()` restituisce quali anelli sono accesi.
Ora `densita.mjs` porta quel vettore in `MARCHIO-STATI.json`, che è versionato.

```
riposo 0 · t0 1 · t1 1 · ascolto 1 · t2 1 · subagent 1 · offline 0 · warn 0
onda 5 su 5      ← dichiarata: non è uno stato, è il guscio che PASSA
```

Leggere il sorgente avrebbe detto solo che da qualche parte c'è un
`i === indice`. Questo dice quanti anelli erano accesi davvero.

### Il traffico dell'insegna: un test appeso a un NOME

Cercava `contati++` — il contatore di messaggi di allora. Quel contatore non
c'è più: l'insegna si muove sui **cambi di stato dei nodi** (`cambiati++`),
che è una versione **più forte** della stessa proprietà — un messaggio che non
cambia niente non muove niente.

Il test era rosso mentre il codice era migliorato. È il difetto della riga 113
di `lettura.js`, fissata per numero e rotta da un import: qui era un
identificatore invece di un numero, e la specie è la stessa.

Riscritto sulla proprietà: dentro `aggiorna()` la guardia sulla telemetria
porta a un `return` immediato, **prima** che qualcuno legga il carico.

### Il centro libero: la griglia era il surrogato sbagliato

Chiedeva le colonne centrali libere in **tutte e quattro** le righe. La scena
mette `cartella` in `[5,0,3,1]`, cioè nella riga 0 — e la riga 0 sta **sopra**
il disco: y 36-200 contro un nucleo che comincia a 259. `moduli.js` lo scrive
accanto a quella cella, con la misura: «disco coperto 0,0 %».

Il test era rosso contro una scena che rispetta §25.1. Chiedeva una banda
libera da cima a fondo quando la proprietà è un'altra: **il nucleo non
dev'essere coperto**, e il nucleo non arriva in cima.

Sostituito con la misura. `app/main.js` misura l'occlusione del disco nella
finestra viva con `elementFromPoint`, passo 2 px; `densita.mjs` porta quel
valore in `DENSITA.json`.

```
nucleo: raggio 162,9 · 7,00 % del pavimento · coperto dai pannelli 0,81 %
```

**La soglia è 2 %, e sta in mezzo a due casi misurati**: 0,81 % è il residuo
dei bordi che sfiorano il disco oggi; 6,7 % è quanto copriva la cella provata
prima (`[4,3,4,1]`, sotto il disco) e scartata guardando lo scatto. Una soglia
deve saper separare due casi, e questa lo fa.

## 3. Un catch muto, di nuovo

Portando l'occlusione nell'esito, il valore usciva `null`. Il `catch` che
avevo scritto era muto, e per un minuto è sembrato che l'occlusione mancasse.
Fatto parlare:

```
(nucleo non misurato: a is not defined)
```

Un nome di variabile sbagliato. **È lo stesso difetto già corretto in questo
stesso file**, dove un `catch { return null; }` aveva prodotto `impronta: null`
per un `ReferenceError` che nessuno vedeva. Un valore assente sembra una misura
mancante invece di un guasto.

## 4. Verifica

| | |
|---|---|
| `tests/eval_visual.py` | **47 passed** (erano 41 con 5 rossi) |
| `uv run pytest -q` | **1067 passed** (erano 792, e 275 non venivano eseguiti) |
| densità | rimisurata **dopo** la modifica a `moduli.js`, `DENSITA' CONFORME` |

**Ritirata una correzione per volta:**

| ritirato | esito |
|---|---|
| due anelli accesi insieme nella misura | 1 rosso |
| la misura senza il vettore degli anelli | 1 rosso |
| il nucleo coperto al 6,7 % | 1 rosso |
| il nucleo con raggio zero | 1 rosso |
| la misura senza l'occlusione del nucleo | 1 rosso |
| la telemetria che entra nell'insegna | 1 rosso |
| la guardia dopo la lettura del carico | 1 rosso |

## 5. Perché la misura è rifatta due volte

La prima volta avevo rigenerato solo `DENSITA.json` dal PNG esistente. Ma
avevo toccato `moduli.js` **dopo** lo scatto: l'impronta avrebbe certificato
sorgenti più nuovi dell'immagine da cui vengono i numeri — cioè esattamente il
difetto di provenienza che §11.7 regola 5 vieta. Rifatto tutto il giro:
Electron, scatto, misura. Numeri invariati.

## 6. Dichiarato aperto

1. **La soglia del 2 % sul nucleo è mia**, scelta fra due casi misurati. Se un
   giorno una scena la sfiora da sotto, il numero va guardato di nuovo insieme
   allo scatto — non alzato.
2. **`onda` accende tutti gli anelli**, ed è dichiarata come eccezione. Se
   qualcuno introducesse un secondo stato-non-stato dovrebbe aggiungerlo qui, e
   il test lo costringe a farlo.
3. **I 275 test che ora girano non li ho riletti uno per uno.** Sono verdi, ma
   verde non vuol dire che verifichino ancora ciò che dicono di verificare —
   tre dei cinque di oggi erano verdi per anni prima di diventare falsi.
