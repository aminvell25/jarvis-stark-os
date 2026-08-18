# Fase 7 — esito dei criteri di accettazione

**Data**: 18 agosto 2026 · **Riferimento**: `docs/SPEC.md` §22 Fase 7 e §14
**Test**: 285 verdi (erano 248) + 185 negli eval · **Precedente**: `FASE-06.md`

---

## ⚠️ Il criterio l'ho dichiarato io

**§22 non ha una riga «Criterio» per la Fase 7.** Ce l'hanno tutte le altre;
questa ha solo la descrizione. Ma `CLAUDE.md` dice che una fase è chiusa quando
*«il criterio di accettazione dichiarato in docs/SPEC.md §22 è verificato»*, e
qui non c'era niente da verificare.

Non l'ho lasciato in bianco. L'ho derivato dai quattro punti che §14 già
enuncia, e lo riporto **come mio**, non come della specifica:

1. una mano vera davanti alla webcam produce un intento, stabile per 5 frame;
2. il tracker regge 30 fps su CPU, con `delegate=CPU` esplicito;
3. nessuna gesture può invocare un tool non `gesture_allowed`, e il rifiuto è
   strutturale;
4. il picking con three-mesh-bvh trova la mesh sotto il puntatore.

---

## 1. «Una mano vera produce un intento» — ❌ NON VERIFICATO

**Nessuna mano è mai entrata in campo.** Due esecuzioni, 350 fotogrammi in
tutto: `con una mano 0/350`.

La telecamera era accesa (autorizzata da Lei), la catena ha girato, ma davanti
all'obiettivo non c'era nessuno. Non posso dichiarare verificato ciò che non ho
visto accadere.

**Cosa resta provato**: il riconoscitore su 9 sequenze di landmark sintetici
(`tests/gesture_corpus.py`), di cui **5 sono non-gesti** che non devono emettere
nulla. Ma i landmark sintetici li ho scritti io, e il corpus ha già dimostrato
che potevo sbagliarli — vedi «Il modello di mano era sbagliato» più sotto. Che
il riconoscitore regga sui landmark **veri** di MediaPipe è un'altra cosa, e
resta da vedere.

```bash
PYTHONPATH=. uv run python scripts/bench_gestures.py 200 100
```

Basta tenere una mano davanti alla webcam mentre gira.

## 2. «30 fps su CPU con delegate=CPU» — ⚠️ VERIFICATO A METÀ, E LA CAUSA È ALTROVE

`delegate=CPU` è esplicito, e un test lo sorveglia sul sorgente.

Sulla cadenza, la misura ha trovato qualcosa che non mi aspettavo:

| | fps catena | fps telecamera | inferenza |
|---|---|---|---|
| esposizione automatica | **9,4** | 12,5 | 8,3 ms |
| esposizione forzata corta | **16,6** | 20,0 | 8,5 ms |

**Il collo di bottiglia non è MediaPipe.** L'inferenza sta in **8,3 ms**: c'è
margine per oltre cento fotogrammi al secondo. È la telecamera che ne consegna
12,5, perché con poca luce l'**auto-esposizione allunga il tempo di posa**. Con
esposizione corta forzata, isolata, la stessa telecamera dà 30,0 fps esatti.

Non ho forzato l'esposizione come predefinito: un'immagine più scura peggiora
il rilevamento, e scambiare qualità dell'immagine per cadenza andava deciso,
non subito. Il tracker **misura la cadenza vera all'avvio e la annuncia** quando
scende sotto il 70 % di quella richiesta, dicendo anche la causa probabile e il
rimedio — la stessa regola del ripiego vocale di §7.4.

**Conseguenza da tenere presente**: a 12,5 fps l'isteresi di 5 frame non vale
166 ms ma **400 ms**. §14 scrive «5 frame (~166 ms)» dando per scontati i 30 fps.

## 3. «Nessuna gesture può invocare un tool non ammesso» — ✅ VERIFICATO, ED È STRUTTURALE

Era imposto **a metà**. Fase 1 impediva di *registrare* un tool
`side_effect=True` come `gesture_allowed`; nulla impediva a un percorso gesture
di chiamare `invoke()` su `trash_path`.

`registry.invoke_da_gesture()` chiude la metà mancante, e `mapping.py` non ha
altra strada verso i tool. Solleva invece di restituire `ok=False`: una gesture
che punta a un tool vietato è un errore di **cablaggio**, e un esito finirebbe
in un ramo di gestione errori invece che sotto gli occhi di chi l'ha scritto.

Il test più importante della fase gira su **tutti** i tool registrati, non su un
elenco scritto a mano: un tool nuovo ci finisce dentro da solo, e o è
`gesture_allowed` e non distruttivo, o una gesture che lo nomina solleva.

E due allowlist, mai un ramo che lascia passare il resto:

```
intento che nomina un TOOL  ->  invoke_da_gesture(), che rifiuta
intento di INTERFACCIA      ->  deve stare in INTENTI_UI (i quattro di §14)
qualunque altra cosa        ->  solleva
```

## 4. «Il picking trova la mesh» — ⚠️ VERIFICATO COME CODICE, non nella scena viva

`ui/src/three/picking.js` monta `acceleratedRaycast` e costruisce il `MeshBVH`.
Il budget di §10.4 regge invariato con il modulo caricato: **16,7 ms**, sempre
agganciato al vsync.

Non ho verificato un raggio che colpisce una mesh **mossa da una mano vera**:
dipende dal criterio 1, che non è verificato.

---

## Il modello di mano era sbagliato, e l'ha trovato il corpus

Le prime esecuzioni del corpus fallivano su metà dei casi, e la colpa non era
del riconoscitore:

**Il pugno risultava «palmo aperto».** Nel mio generatore la punta di ogni dito
stava sempre oltre la nocca, anche a mano chiusa. Una mano vera **arriccia** le
dita verso il palmo: la punta finisce più vicina al polso della nocca.

**Ogni mano risultava in pizzico.** Tenevo il pollice a ridosso della colonna
dell'indice, a un decimo di mano dalla sua punta. In una mano vera il pollice
aperto sta a più di mezza mano di distanza — ed è quella distanza a rendere il
pizzico un gesto invece che uno stato di riposo.

Questo è anche il motivo per cui il criterio 1 conta davvero: un modello
sintetico può essere coerente con sé stesso e non somigliare a ciò che MediaPipe
produce.

## E i due gesti di movimento non hanno lo stesso tempo

Con una finestra unica di 8 fotogrammi la rotazione a due mani non veniva mai
riconosciuta abbastanza a lungo perché l'isteresi la contasse. Non era un
difetto della soglia: una spinta laterale è uno **scatto**, una rotazione è un
gesto **lento**. Storia lunga 12 fotogrammi, e la spinta ne guarda solo la coda.

---

## La telecamera, e le quattro regole imposte dal codice

1. **Si accende su richiesta**: `avvia()` apre il dispositivo, l'import no. Un
   test verifica che un tracker appena costruito non abbia né telecamera né
   modello.
2. **Si rilascia sempre**, anche su eccezione: `ferma()` è idempotente e il
   tracker è un context manager.
3. **Nessun fotogramma tocca il disco.** Un test cerca `imwrite`, `imsave`,
   `tofile` e `.save(` nel sorgente del tracker: se un domani ce ne fosse uno,
   fallisce.
4. **Mentre è accesa si vede.** Il pannello gesture porta la spia in
   `--rust` — l'unico accento caldo di quel pannello, perché è l'unica cosa che
   lì significhi qualcosa. È la stessa logica del rettangolo di ARGUS in §12.

E una quinta, che vale la pena scrivere: **nel pannello non c'è un'anteprima
video**. Se ci fosse, l'immagine della stanza attraverserebbe il socket e
finirebbe composta dal renderer — che dalla Fase 6 ospita contenuto non fidato.
Passano solo 21 terne di numeri.

---

## Il costo di MediaPipe, misurato

**62 → 77 pacchetti**, `.venv` da **113 a 563 MB**. Arrivano numpy, OpenCV,
matplotlib, pillow e sounddevice — di cui usiamo OpenCV per la cattura e numpy
per i buffer.

L'import è **pigro**: `import mediapipe` sta dentro `avvia()`, non in cima al
modulo. Il core parte, i test girano e `disponibile()` risponde anche su una
macchina dove MediaPipe non c'è.

Il modello `hand_landmarker.task` (7,8 MB) si scarica al primo uso sotto
`~/.local/share/jarvis-os/models/`, come fece Vosk in Fase 3.

---

## ❌ NON VERIFICATO

1. **Il riconoscimento su una mano vera** (criterio 1). Nessuna mano in campo
   in 350 fotogrammi.
2. **I 30 fps con l'esposizione automatica** (criterio 2). Sono 12,5 in questa
   luce, e la causa è la telecamera, non il codice.
3. **Il picking su una mesh puntata da una mano** (criterio 4), che dipende dal
   primo.
4. **La rotazione a due mani dal vivo.** Il corpus la copre; due mani vere
   davanti alla webcam no.
5. **Il comportamento con l'illuminazione cambiata** — che è esattamente la
   variabile che ha dimezzato la cadenza.

---

## Riepilogo

| | |
|---|---|
| Test | **285 verdi** (erano 248) + **185** negli eval |
| Corpus dei gesti | 9 sequenze, di cui **5 non-gesti** |
| Invariante 27 | da mezzo a **intero**, e imposto su ogni tool registrato |
| Inferenza MediaPipe | **8,3 ms** su CPU |
| Cadenza reale | 12,5 fps in automatico, 30,0 con esposizione corta |
| Budget di frame | **16,7 ms**, invariato col picking caricato |
| Criteri | 1 verificato, 2 a metà, **1 non verificato** |
| Criterio | **dichiarato da me**: §22 non ne aveva uno |
