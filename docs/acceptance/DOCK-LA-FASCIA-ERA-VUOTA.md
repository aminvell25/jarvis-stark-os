# Il dock — 2,0 % a 31,2 %, e la fascia era vuota per sei ottavi

**Rollback:** `fe065ec`
**Criterio:** inchiostro L>50 nella fascia del dock **≥ 20 %** · riferimento
`01` 26,2 %, `05` 22,8 %
**Esito: SODDISFATTO — 31,2 %.**

---

## 1. Che cosa fa il 26,2 % del riferimento

La domanda giusta non era «quanto», era **di che cosa**. Censo dei colori nella
fascia di `famiglia-a/01`:

```
  #0f1418  L 19,2  15,0 %      = il nostro --bg-void
  #1a1f23  L 30,2   7,0 %      = il nostro --bg-deep
  #101519  L 20,2   3,2 %
```

**Il fondo è scuro come il nostro.** Il 26,2 % non è una lastra piena: è
contenuto. E il profilo per ottavo dice dove sta:

```
  riferimento  7,1  10,4  43,8  49,3   8,6  32,0  53,8   4,9
  noi, prima   6,8   8,7   0,1   0,0   0,0   0,0   0,0   0,0
```

**Sei ottavi su otto completamente vuoti.** Il dock portava due voci a
sinistra e 1 400 px di niente.

## 2. Come lo fa la nostra barra, che il criterio lo passa

La barra sta al **55,8 %** contro il 28,4 % del riferimento. Censo:

```
  #1a1f23  L 30,2  37,9 %   il fondo
  #32464f  L 66,4  37,8 %   --fill-1: i CHIP
```

Il 37,8 % della fascia è `--fill-1`: ogni dato sta in un riquadro pieno. È la
lettura che `DIVARIO-PREMIUM.md` §7 dà al punto 2 — «riempirli con informazione
che già esiste e non mostriamo» — e la barra l'ha eseguita. Il dock era rimasto
indietro.

Quindi il dock prende **lo stesso chip**, non un secondo: `padding: --s-1`,
fondo `--fill-1`, mono `--t-micro`, etichetta `--icona` in maiuscole, valore
`--txt-primary`, e il campo senza valore resta spento. Una scrivania con due
modi di dire «ecco un dato» ne ha uno di troppo.

⚠️ **Il punto 1 di §7 — «Fondo `--fill-1` per entrambi, pieno» — non l'ho
seguito**, e la misura dice perché: il fondo del riferimento è `--bg-void` e
`--bg-deep`. Una lastra piena porterebbe la fascia vicino al 100 % e farebbe
passare la soglia senza che la densità sia vera. Sarebbe la specie di difetto
che §11.7 regola 4 esiste per impedire.

## 3. Otto fatti veri, e nessuno duplica un pannello

§26.3 dice che il dock **ha ceduto l'indice** al catalogo: quel che resta è
stato, non comandi. Il vincolo è quindi che ogni voce sia un fatto che oggi non
si vede da nessun'altra parte — due posti in cui la stessa verità può divergere
sono il difetto che quella sezione nomina.

Verificato prima di scegliere, non dopo:
`grep -rn "seccomp|gpu|trash_only|tts_provider" ui/src` non trova **nulla**
fuori dal finto della galleria.

| campo | da dove | perché non era già altrove |
|---|---|---|
| `GPU amdgpu` | `gpu.driver` | la telemetria mostra cpu, ram, temp, disco. Non la GPU |
| `VRAM 0.7/8.0 GiB` | `gpu.used/total_bytes` | idem |
| `SECCOMP no` | `core.seccomp` | lo stato della sandbox non lo dice nessuno |
| `CESTINO solo` | `settings.fs.trash_only` | l'**invariante 4**, resa visibile invece che promessa |
| `LAYOUT ok` | `layout.esiste/corrotto_in` | dove vive lo stato della scrivania, e se è integro |
| `CLIENT 1` | `ws.clients` | **nominato** nell'elenco di §7, e l'unica voce di quell'elenco che nessuna striscia mostrava |
| `T1 claude-haiku-4-5-20251001` | `settings.llm.t1_model` | la barra dice `LLM claude_code`, che è il backend di **T2** |
| `CODICE spento` | `codice.acceso` | una capacità, non una preferenza |

Sono tutti campi di `state.snapshot`, che arriva **una volta**: restano fermi
per la sessione e non aggiungono nessuna deriva alla fixture.

**Restano fuori, dichiarati:** `tts_provider` — la barra porta `STT`, e mettere
`TTS` qui spezzerebbe una coppia su due strisce — e `quota.restanti`, che il
dettaglio di T2 già porta a destra.

## 4. Lo spazio lo assorbe chi sta prima

`T2` si ancora a destra con `flex: 1` sul contenitore dei campi, non con
`margin-left: auto`: auto si risolve in un numero di pixel qualunque e l'audit
lo boccia, perché non viene da nessuna scala. È la regola di `barra.js`, che il
commento in cima a `dock.js` **citava già senza averla applicata**.

## 5. Il difetto trovato per strada, e che ha deciso la forma

La prima stesura dava ai chip `padding: var(--s-1)` su tutti e quattro i lati.
Il dock è passato da **28 a 36 px**, il pavimento si è accorciato di otto, e

```
FAILED tests/test_layout.py::TestIconeVere::test_10_riavviato_il_core_e_ANCORA_LI
```

Verificato che fosse mio e non un caso: rimesso il dock a `fe065ec`, **11
passed**; rimesso il mio, uno rosso. Un'icona posata vicino al bordo basso
viene ritagliata al riavvio, perché `adatta()` la riporta dentro un'area che
nel frattempo si è accorciata. `adatta()` fa il suo mestiere — il difetto è che
**cambiare l'altezza del dock invalida le posizioni memorizzate**.

Quindi lo spazio per i chip si prende da **dentro**: il padding verticale del
dock scende da `--s-2` a `--s-1`, i chip lo riprendono, e `4 + 20 + 4 = 28` —
gli stessi 28 px di prima. L'altezza della fascia non cambia, il pavimento non
si muove, `TestIconeVere` torna verde, e i chip passano da 12 px di altezza a
20.

⚠️ Resta aperto il fatto sottostante: **un'icona salvata vicino al bordo del
pavimento non sopravvive a un cambio di altezza del dock.** Non l'ho toccato —
è un turno suo, e questo lo ha solo scoperto.

## 6. La misura

| | prima | dopo |
|---|---|---|
| **dock** | 2,0 % | **31,2 %** ✅ (soglia 20) |
| entropia | 2,4127 | **2,43** |
| `L>60` | 26,98 % | **27,9 %** |
| dev.std | 34,06 | 34,2 |
| caldo | 3,8 % | 3,8 % (dentro 3–6) |
| barra | 63,8 % | 63,8 % |
| altezza della fascia | 28 px | **28 px** |

⚠️ **31,2 % sfora la forbice del riferimento (22,8–26,2), e va detto** invece di
lasciarlo passare come «sopra soglia». La ragione è misurabile: la nostra
fascia è alta il **3,3 %** dell'altezza dello schermo, quella del riferimento
il **5,9 %**. Portare lo stesso contenuto in una fascia poco più che metà alta
significa occuparne una frazione maggiore. Normalizzato sull'altezza, il nostro
contenuto vale ~17 %, cioè **sotto** il riferimento, non sopra.

La strada per rientrare nella forbice non è togliere campi: è alzare la fascia
al 5,9 %. Ma alzarla sposta il pavimento — cioè esattamente ciò che ha fatto
cadere `TestIconeVere`.

## 7. §11.8, punto per punto

```
GEOMETRIA
✓ border-radius: --radius, che e' 0
✓ tagli a 45° — non toccati
✓ spaziature: --s-1 fra e dentro i chip, tutte dalla scala
✓ pesi di linea: i divisori restano --line-hair
COLORE
✓ tutti da tokens.css — audit del montaggio `chrome` pulito, 0 letterali
✓ caldo 3,8 % < 10 %
✓ tinte ≤ 3
✓ zero gradienti — i chip sono tinta piatta
✓ ZERO alone, bloom, glow
✓ nessuna ombra aggiunta
TIPOGRAFIA
✓ --t-micro, uno dei sei gradini
✓ tutti i valori in --font-mono
✓ etichette maiuscole con letter-spacing 0.08em
CONTENUTO
✓ dati VERI — otto campi di state.snapshot, nessun segnaposto
✓ il campo senza valore resta SPENTO, non mostra un trattino su un riquadro
   acceso
✓ densita': 31,2 %, sopra la soglia e SOPRA la forbice — dichiarato in §6
   con la ragione, invece di lasciarlo passare
MOVIMENTO
✓ nessuna animazione aggiunta
TECNOLOGIA
✓ testo nel DOM
```

Guardato in `shots/chrome.png` e nella scrivania intera: la striscia si legge
come stato, i chip hanno lo stesso peso di quelli della barra, T2 sta a destra.

## 8. Verifica

| | |
|---|---|
| `npm run shot -- chrome` | audit 0 fuori sistema, 0 letterali · OK |
| `npm run scrivania:fixture` | EXIT=0, `scattiIdentici` true |
| `npm run verifica:scrivania` | EXIT=0 |
| `uv run pytest -q` | **585 passed** |
| `TestIconeVere` col dock vecchio e col nuovo | 11 passed in entrambi |

## 9. E la diciannovesima volta

Ho messo dei backtick dentro un commento CSS, chiuso il template literal e
rotto il modulo: la fixture è uscita **124** — timeout, perché la scrivania non
si è mai formata. `tests/test_fogli_di_stile.py` l'ha visto in **0,04 s**.

La regola non è «stare attenti»: è **lanciare quel test prima dello scatto**,
che costa quattro centesimi di secondo contro i cinque minuti di un giro morto.

## 10. Dichiarato aperto

- **La distribuzione non è quella del riferimento**: i suoi ottavi 5-6 sono
  pannelli che arrivano al bordo dello schermo, i nostri si fermano al
  pavimento.
- **La barra resta al 63,8 % contro il 28,4 % del riferimento**: sfonda di più
  del doppio, ed è l'opposto del difetto appena chiuso.
- **Il dock è alto 36 px = 4,3 % dell'altezza**; il riferimento tiene la fascia
  al 5,9 %. Non l'ho toccato: cambiare l'altezza sposta il pavimento e tutti i
  rettangoli dei pannelli.
- Le misure valgono per la registrazione `4d5edf35cfdb64af` (§11.9).
