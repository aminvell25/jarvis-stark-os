# I tre ritagli sono due, e l'accordo si misura

**Rollback:** `16f802b`
**Criterio:** «una proprietà, un proprietario» applicata al ritaglio dentro
l'area.
**Esito: dentro il renderer il proprietario è uno. Attraverso il confine col
core sono due, e un test li fa girare sulla stessa tabella.**

---

## 1. Divergevano su due assi, non su uno

`16f802b` ne ha chiuso uno — lo **spazio di coordinate** — e ha lasciato aperto
il fatto sottostante. Unificando è saltato fuori il secondo, che nessuno aveva
mai visto:

| | banda per `y` | minimo |
|---|---|---|
| `geometria-area.js` (pannelli) | `[alto, alto + h − min]` | **80** |
| `icone.js` (icone e cartelle) | `[alto, alto + h − min]` | **40** |
| `core/layout.py::adatta` | `[alto, alto + h − min]` | **80 per tutto** |

Il core applicava alle icone il minimo dei **pannelli**. Restava una fascia di
40 px in cui il renderer accettava una posizione e il core la spostava — la
stessa specie del difetto appena chiuso, un asse più in là.

### Perché nessuno l'aveva visto

Perché `icone.js` scriveva, accanto al proprio 40:

> Quanto di un'icona resta a schermo quando l'area si stringe. **Stesso numero
> e stessa ragione** del `MIN_VISIBILE` dei pannelli.

**Non era lo stesso numero.** Il commento affermava un'uguaglianza falsa, e un
commento che afferma un'uguaglianza è esattamente ciò che una misura deve
sostituire.

E il test del core diceva la stessa cosa al contrario:

> `1000 - 80`: lo stesso `minimo_visibile` dei pannelli. Un'icona è più piccola
> di una finestra, quindi il margine la tiene tutta a schermo.

Il ragionamento è giusto e porta alla conclusione **opposta**: più piccola vuol
dire che ne basta meno a schermo — cioè il 40 che il renderer usava già.

## 2. Dentro il renderer: da due a uno

`geometria-area.js` diventa il proprietario della **regola**:

```javascript
export const MIN_VISIBILE = 80;
export const MIN_VISIBILE_ICONA = 40;

export function dentroPunto(x, y, a, minimo = MIN_VISIBILE) { … }
```

- `dentroArea(p, a)` — i pannelli — è adesso `dentroPunto` più il ritaglio
  della **dimensione**, che è l'unica cosa che un pannello ha in più di un
  punto. Le due righe scritte a mano erano il posto da cui la copia era nata.
- `icone.js` importa `dentroPunto` e `MIN_VISIBILE_ICONA`. Il suo `dentroArea`
  resta, ridotto a ciò che non poteva stare in una funzione pura: **contro
  quale area**, che dipende dalla scrivania.

Le due soglie stanno adesso **una accanto all'altra**, dove la differenza si
vede invece di essere affermata da lontano.

## 3. Attraverso il confine: l'accordo si misura

Fra Python e JavaScript non si importa. Il rimedio del progetto per un fatto
che vive dall'altra parte di un confine esiste già in
`tests/test_geometria_area.py`: eseguire il modulo **vero** con
`node --input-type=module`.

`TestITreRitagliSonoUNO` fa girare la stessa tabella nei due linguaggi:

- **3 aree** — la scrivania con il dock di oggi, la stessa col dock cresciuto
  di otto pixel (la differenza che ha fatto emergere il primo difetto), e
  un'area **senza barra**, cioè il caso in cui i due ritagli coincidevano anche
  prima e che quindi non provava niente;
- **7 punti** — dentro, sui due bordi, appena oltre, molto oltre in entrambi i
  versi. `-40` e `9999` non sono decorazione: sono i due lati che `max` e `min`
  trattano separatamente;
- **21 casi × 2 soglie**, confrontati uno per uno.

Più due asserzioni che un confronto di risultati non dà:

- **le due soglie sono gli stessi numeri**, letti dal modulo JS e confrontati
  con le costanti Python;
- **`icone.js` non ha più una copia della regola** — un controllo sul
  sorgente, come `TestR82`, perché un confronto di risultati non distingue «la
  copia è sparita» da «la copia è rimasta uguale per ora».

### La prova che bocciano

| cosa ho rimesso com'era | esito |
|---|---|
| `MINIMO_ICONA = 80` nel core | 2 rossi: le soglie e la tabella delle icone |
| la copia della regola dentro `icone.js` | 1 rosso: il controllo sul sorgente |

## 4. Che cosa cambia sulla scrivania

**Niente.**

```
scrivania.png e prima.png: IDENTICI, 0 pixel di differenza
```

Ed è giusto così: la regola corretta morde solo ai bordi, e sulla scrivania di
oggi nessuna icona sta in quella fascia. Un'unificazione che avesse spostato
qualcosa avrebbe voluto dire che stavo cambiando il comportamento, non
riunendolo.

| | |
|---|---|
| dock | 24,2 % |
| entropia | 2,44 |
| `L>60` | 28,0 % |
| caldo · barra | 3,7 % · 63,8 % |

## 5. E ho riavviato il core prima di credere ai test

Il documento di ieri chiudeva con una regola scritta dopo esserci cascato due
volte: **dopo aver toccato uno schema del core, il core si riavvia prima di
credere a un test end-to-end.**

Qui ho toccato `core/layout.py` dopo l'ultimo riavvio. L'ho riavviato prima di
lanciare `TestIconeVere`, che infatti dà **11 passed**. La regola ha pagato al
primo turno in cui esisteva.

## 6. Verifica

| | |
|---|---|
| `tests/test_geometria_area.py` | **8 passed** (era 4) |
| `TestIconeVere` col core riavviato | 11 passed |
| `npm run scrivania:fixture` | EXIT=0, PNG identico a prima |
| `uv run pytest -q` | **596 passed** |

## 7. Dichiarato aperto

- **Restano due implementazioni**, una per linguaggio, e non è eliminabile
  senza spostare il ritaglio da una parte sola del confine. Ciò che è
  eliminabile è che **divergano senza che nessuno se ne accorga**, e quello è
  chiuso: 42 confronti a ogni giro di suite.
- **La tabella dei casi è autorevole quanto chi l'ha scritta.** Se un caso che
  conta non è nella tabella, i due possono divergere lì. Le tre aree e i sette
  punti coprono i bordi che conosco; non è una prova esaustiva, è una prova di
  regressione.
- **`adatta()` ha ora due parametri di soglia** — `minimo_visibile` per i
  pannelli e `minimo_icona` per il fondo. Un terzo genere di oggetto ne
  vorrebbe un terzo, e a quel punto la firma chiede di diventare una tabella.
