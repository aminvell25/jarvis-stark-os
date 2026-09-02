# Il pilastro 3D — `tubo_piegato`, la fetta 2

**Data**: 3 settembre 2026 · **Riferimento**: ADR-014
(`docs/PERIMETRO-E-DECISIONI.md`), `docs/SPEC.md` §17.1-17.3 e §17.4 ②,
invarianti 22, 34, §11.10 regole 2, 3, 4, 5 e 7 ·
**Rollback**: il commit precedente · **Test**: 2174 → **2207** passati
(2232 raccolti, 25 saltati, 33 nuovi)

---

## ⚠️ Che cosa c'era prima, e perché è stato buttato

La prima stesura di questa fetta faceva ciò che §17.4 ② dice **alla lettera**:
una spline Catmull-Rom **chiusa** su un guscio generato da due armoniche,
spazzata in tubo. La matematica era giusta e misurata — passava per i punti di
controllo a 1,5·10⁻¹⁴ mm, il telaio si chiudeva senza cucitura, la topologia
era un toro — e **l'oggetto non era un pezzo**:

- misure **risultanti** invece che di progetto: 214,9 × 202,0 × 67,6 mm;
- un'asimmetria che si leggeva come un errore invece che come una scelta,
  cioè l'opposto esatto di §11.10 regola 4;
- un tubo grasso su un anello senza un tratto dritto né un raggio
  riconoscibile: organico dove il riferimento di famiglia-a è tecnico.

Il proprietario l'ha respinto **guardandolo**, ed è §11.7: una violazione si
riscrive, non si rattoppa. Il pezzo sta al commit `cd5dbbd` e si recupera con
un checkout.

Avevo scelto quel guscio perché esercitava la matematica della spline, non
perché fosse una cosa che qualcuno vorrebbe. È il difetto: ho ottimizzato per
il criterio, non per l'oggetto.

## Che cos'è adesso

Un **tubo piegato**: corse dritte raccordate da pieghe a raggio costante. È
esattamente come si programma un tubo su una macchina — corsa, rotazione,
angolo — e le tre parole sono i parametri del generatore. Le misure sono tonde
perché sono di progetto: Ø12, R24, corse 90/70/45/60, angoli 90°/60°/90°.

E `segmenti_per` ci sta meglio di prima: è nata per un arco di cerchio, e qui
gli archi sono cerchi veri. Nella stesura precedente si passava «il raggio del
cerchio che ha la stessa lunghezza della curva», che era una perifrasi.

## Che cosa è rimasto della fetta precedente

Tutta la macchina, che era la parte buona: sezione spazzata lungo un percorso,
telaio a torsione minima, densità dalla curvatura, `Modello` con la tolleranza
dichiarata, verificatore che rilegge il GLB con la libreria standard, e il
**gemello** `segmenti_per` / `segmentsFor()` con il test che li esegue insieme.

Se n'è andata la **chiusura del telaio**: il percorso è aperto, e il residuo di
torsione dopo un giro non esiste perché non c'è un giro. Con lei il suo test,
che teneva una proprietà che questo pezzo non ha.

---

## Le tre cose che questa fetta ha dovuto risolvere

### ① Il gemello, e perché non se ne può cancellare uno

`core/model3d/parametrico.py::segmenti_per` è
`ParametricComponent.segmentsFor()` riga per riga. Non è una duplicazione da
togliere: §17.2 mette il generatore nel core e il componente che lo incassa nel
renderer, e la regola della densità è dell'uno e dell'altro. La cura è renderle
**verificabili insieme** — `TestIlGemello` le esegue entrambe su dodici
ingressi scelti dove due implementazioni divergono: i due estremi del clamp, un
quoziente esattamente intero dove `ceil` non deve aggiungere uno, archi
parziali, corde diverse dalla predefinita.

### ② Il bounding box non è «la linea d'asse più il raggio»

La prima stesura del tubo piegato lo diceva, e il presidio di §11.10 regola 7
l'ha preso **subito**, con 7,8 mm di scarto su X.

Il disco della sezione sta nel piano **perpendicolare alla tangente**: dove il
tubo corre lungo un asse, su quell'asse non sporge affatto. La forma esatta
esce dall'ortonormalità del telaio — il punto a `c + r(cos φ·n + sin φ·b)` ha
estensione massima `r·√(n_k² + b_k²)` sull'asse k, e `n_k² + b_k² = 1 − t_k²`.
Si calcola dalla sola **tangente**, senza toccare né il telaio né i vertici
emessi: è quindi una seconda affermazione indipendente, ed è ciò che rende
§11.10 regola 7 un controllo invece di un'eco.

Resta la tolleranza del poligono inscritto, `2·r·(1 − cos(π/lati))` = **0,058
mm** con 32 lati, con la ragione obbligatoria: **una tolleranza senza una
ragione scritta non si costruisce**.

### ③ Le quote le sceglie il generatore, non il pannello

Guardando lo scatto: il pannello annotava sempre i tre lati del bounding box.
Su una piastra funziona — il bbox **è** il pezzo — e su un tubo piegato no:
177,6 × 113,1 × 153,6 sono un risultato, appesi a tre angoli che stanno nel
vuoto.

`Modello` guadagna `quote`: testo già scritto e punto di ancoraggio, dichiarati
dal generatore. La piastra annota i suoi tre lati e il foro; il tubo annota
**Ø12**, **R24** e lo **sviluppo** — i due numeri che si ordinano e quanto tubo
serve. Il pannello li proietta e basta, che è tutto quello che il renderer può
sapere di un pezzo che non ha generato.

---

## Verifica

### ✅ Le proprietà del percorso e della superficie

| | |
|---|---|
| topologia | `is_watertight`, **`euler_number == 2`** — genere zero: un tubo aperto con due tappi. L'anello di prima dava 0 |
| corse dritte | il versore della tangente non cambia lungo una corsa, a 10⁻⁹ |
| pieghe | raggio costante a 10⁻⁶ mm, misurato dal centro ricavato da tre punti dell'arco |
| conteggi | 2882 vertici e 5760 triangoli, uguali a `conteggi_di` — che li calcola **senza spazzare niente** |
| bbox | dichiarato = misurato a 0,01 mm, con la formula dalla tangente |

### ✅ Dal vivo, «genera un tubo»

Il tool è lo stesso: T0 → planner → conferma col percorso risolto → `trimesh`
scrive → il verificatore rilegge con `struct` e `json` → `fs.result`, riga di
diario col verdetto, `model3d.preview` al pannello.

⚠️ **La quota detta è il DIAMETRO del tubo**, come in officina: «un tubo da
venti» è un tubo da venti millimetri. Le corse e gli angoli non si dicono a
voce — sono dodici numeri, cioè un disegno — e si cambiano dalla pagina o da un
turno successivo.

⚠️ **E il raggio di piega SEGUE il diametro**, trovato provando la frase vera:
«fammi un tubo da 20 millimetri» falliva con «sotto 1,5 diametri il tubo si
schiaccia», perché il diametro cambiava e il raggio restava quello del tubo
predefinito. Su una piegatrice la matrice si sceglie per il tubo: chiedere un
diametro senza dire la piega vuol dire «la piega normale per questo tubo», che
è due diametri.

### ✅ Otto bocciature, otto rossi — ma due sono arrivate dopo

| sabotaggio | esito |
|---|---|
| il gemello JavaScript diverge di un segmento | rosso, e nomina i tre ingressi che divergono |
| il clamp Python cambia estremo | 2 rossi |
| il conteggio non viene più dalla formula | rosso |
| il bbox torna «asse più raggio pieno» | 2 rossi |
| i tappi spariscono | 2 rossi |
| il raggio di piega non segue più il diametro | rosso |
| il raccordo non è più a raggio costante | rosso |
| le quote spariscono dal messaggio | ⚠️ **NIENTE da fare: 63 test deselezionati** |

⚠️ **L'ottava bocciatura non ha trovato niente da rompere.** `pytest -k quote`
deselezionava tutti e sessantatré i test: il meccanismo delle quote era
costruito e **non sorvegliato**. Ci sono cinque presìdi adesso — ogni forma
dell'allowlist ne dichiara almeno una, le quote del tubo sono di progetto e non
di risultato, quelle della piastra sono i suoi tre lati, arrivano al renderer,
e il pannello non le sceglie più — e tre sabotaggi che li provano.

### ✅ Il ciclo §11.7

`npm run shot -- modello-tubo` e `-- modello`: audit **0 elementi fuori
sistema, 0 regole con letterali**, font tutti caricati. Il tubo si legge come
una linea idraulica: corse dritte, raccordi tondi, tappi agli estremi, e tre
quote di progetto attaccate al pezzo.

### ✅ Le misure

```
uv run pytest -q -p no:cacheprovider     → 2207 passati, 25 saltati (2232 raccolti)
npm run shot -- modello-tubo             → audit pulito, font tutti caricati
npm run verifica:densita                 → CONFORME, impronta su 118 sorgenti
uv run python scripts/orfani.py          → 5 sospetti, nessuno nuovo
```

| | estrusione_45 | tubo_piegato |
|---|---:|---:|
| vertici | 32 | 2882 |
| triangoli | 64 | 5760 |
| `model3d.preview` | 3,3 KB | 143 KB |
| tolleranza sul bbox | 0 (esatto) | 0,058 mm (0,05 %) |
| quote | 3 lati + foro | Ø, R, sviluppo |

### ❌ NON verificato, dichiarato

- **Che il tubo non si attraversi da solo.** La validazione controlla il raggio
  di piega contro il diametro e le tangenti contro le corse: sono condizioni
  **necessarie e non sufficienti**. Due corse che si incrociano nello spazio
  passerebbero.
- **Il GLB in un visualizzatore esterno o in `gltf-validator`**, come per la
  fetta 1.
- **Il budget di frame dell'invariante 26** con il pannello aperto sulla
  scrivania piena: 2882 vertici contro i 32 dell'estrusione, e la misura vale
  la pena. Non è stata fatta.
- **La finestra Electron vera**: i giri hanno usato la scrivania finta.
- **La parete**: il tubo è pieno, e ciò che si vede è la sua superficie
  esterna. Un tubo cavo vuole un secondo tubo e due corone agli estremi, e
  nessuno l'ha chiesto.

⚠️ **E un test instabile che NON è di questa fetta**:
`test_stop_butta_via_un_ricarico_in_ATTESA` fallisce circa **1 volta su 10** su
`core/settings.py`, che né questa fetta né la precedente toccano — è una corsa
fra un antirimbalzo da 0,4 s e uno `stop()`. Misurato su venti corse prima e
dopo. Dichiarato invece che nascosto.
