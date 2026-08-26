# §12 — ARGUS era scritto per intero e non aveva un chiamante

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §12 · **Rollback**: `436b009`
**Test**: 1288 verdi (erano 1274)

---

## Tre pezzi che non si parlavano

- `core/vision/argus.py` — le due strade, la busta non fidata, il rettangolo
  che viaggia col risultato. **Nessuno costruiva la classe.**
- `ArgusCaptureResponse` in `core/ws_server.py` — validata, e poi **scartata**:
  `on_capture` non veniva passato dalla radice di composizione.
- `catturaEInvia` in `app/main.js` — pronta a rispondere a una domanda che
  nessuno faceva.

Scritti in Fase 6, provati ciascuno per conto suo, mai congiunti. Il risultato:
non si poteva chiedere a JARVIS che cosa c'è sul suo schermo — e nemmeno
percorrere la strada **a costo zero**, che è quella che §12 chiama «la
scorciatoia che quasi tutti mancano».

---

## Le due strade, e due tool

```
domanda su un pannello JARVIS   → ask_state    : zero OCR, zero latenza
domanda sul contenuto <webview> → read_screen  : capturePage + Tesseract
```

### `ask_state` — la scorciatoia

JARVIS **sa già** cosa c'è nei propri pannelli: è lui a mandarne i dati. La
chiave è un percorso puntato dentro lo snapshot (`ws.clients`,
`news_motore.giri_fatti`), e lo snapshot è **lo stesso** che alimenta la
scrivania — una copia divergerebbe.

`gesture_allowed=True`: costo zero, nessun effetto, nessuna cattura. È la strada
che una mano può percorrere senza sorprese.

### `read_screen` — e ciò che ne esce non è fidato

Il testo torna **già avvolto**, con `untrusted: True`, come `read_file` di
Fase 2: la marcatura nasce dove nasce il dato, perché aggiungerla dopo
vorrebbe dire rintracciare tutti i consumatori.

`gesture_allowed=False`, e **non lo vieta l'invariante 27** — non c'è
`side_effect`. È che una mano che fa scattare una cattura dello schermo senza
che nessuno l'abbia chiesta è il contrario del «rettangolo che Le permette di
accorgersi di una cattura inattesa» (§12 punto 3).

E un OCR assente **non somiglia a uno schermo vuoto**: sono due cose diverse e
tornano diverse. Su questa macchina `tesseract` non è installato, quindi è lo
stato reale, non un caso di laboratorio.

---

## La correlazione e la scadenza

Richiesta e risposta viaggiano su un socket asincrono e su **due processi**.

**Un id per richiesta.** Senza, due domande vicine si scambierebbero le
risposte. Con un id fisso il test lo dimostra: la risposta della seconda
sblocca la prima.

**Un timeout, e non è prudenza generica.** `catturaEInvia` **non risponde
affatto** se Electron non è avviato, la finestra è distrutta o la cattura
fallisce — lo dice il suo stesso commento: «il core scade da solo». Senza
timeout la coroutine resterebbe appesa per sempre, e con lei il tool che l'ha
chiamata.

Il valore — 5 s — non è in §12. Viene dal budget di §10.4: un fotogramma è
16,7 ms e `capturePage()` su una finestra 4K ne costa qualche decina. Cinque
secondi sono due ordini di grandezza più del previsto, cioè **«il ponte non
c'è»**, non «il ponte è lento».

---

## Verifica

### ✅ Le tre bocciature

| perturbazione | esito |
|---|---|
| tolto `on_capture` | 1 rosso |
| tolto il timeout | **il test NON FINISCE** — ucciso da `timeout 60` |
| id fisso invece che per richiesta | 1 rosso |

La seconda è la più eloquente: senza timeout il test resta appeso per sempre,
che è esattamente il difetto contro cui il timeout esiste. La dimostrazione è
che il processo va ucciso da fuori.

### ✅ La suite

`1288 passed` (erano 1274).

### ⚠️ Una nota sull'allowlist

I due tool si registrano in `_gradi()` e non nel costruttore, quindi
l'allowlist passa da 25 a **27 dopo l'avvio**. È coerente con la composizione
di ARGUS — che ha bisogno dello snapshot e del socket — ma è diverso dai tool
del volume, che si registrano nel costruttore. La differenza è dichiarata qui
perché il test che conta l'allowlist misura il costruttore e continuerebbe a
dire 25 anche se ARGUS sparisse.

### ❌ NON verificato

- **Il giro completo con Electron vivo.** I due capi sono provati
  separatamente e la correlazione con un socket finto; nessuna cattura vera è
  passata dal ponte in questo turno. È lo stesso punto 3 dei NON VERIFICATI di
  Fase 6.
- **L'OCR.** `tesseract` non è installato e `sudo` è negato dalle regole del
  progetto. Tutti i test dell'OCR girano contro un finto, e la strada che si
  può percorrere davvero oggi è `ask_state`.
- **Il ritaglio a una regione.** `capturePage()` cattura la finestra intera e
  il core non ritaglia: servirebbe Pillow, che non è fra le dipendenze. La
  `Regione` che viaggia col risultato è quindi sempre la finestra.
- **Una cattura 4K vera** contro il limite di 8 MB base64 del contratto.
