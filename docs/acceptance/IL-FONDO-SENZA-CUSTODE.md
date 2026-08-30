# §26.5 — il fondo ha un custode, e la bocciatura che ha cambiato il disegno

**Data:** 30 agosto 2026 · **Riferimento:** `docs/SPEC.md` §26.5, §26.9 punto 4,
§26.10 punto 1 · **Rollback:** `788e493` · **Test:** 1867 → **1868**

Chiude il buco dichiarato il 29 agosto in questo stesso file.

---

## La proprietà, e chi non la custodiva

`ui/src/app.js` decide il ripristino così:

```js
const roba = (layout?.pannelli?.length ?? 0) + suoFondo;
if (!roba) return;
```

Il secondo termine esiste perché una scrivania con le icone sul fondo e nessun
pannello non riparta vuota. **Nessuna prova lo esercitava**, e non per svista:
`test_11` pretende una cartella aperta, e una cartella aperta *è* un pannello.
Misurato a HEAD, nella sezione `riavvio`:

```
ripristino.ricevuti: 7        ← la guardia si attraversa dai PANNELLI, sempre
```

Il ramo `pannelli == 0` non era mai stato preso. Togliere `+ suoFondo` lasciava
verde l'intera classe.

---

## La bocciatura ② ha smentito la sua ipotesi, e il disegno è cambiato

Il piano di questo turno diceva: *chiudere i pannelli non basta a produrre il
caso, perché `onclose` chiama `annuncia()`, che avvisa gli osservatori e non la
persistenza; serve un gesto sul fondo per far scattare la scrittura.* La lettura
del codice lo sosteneva, e la sezione nasceva con quel gesto dentro.

La bocciatura che doveva dimostrarlo necessario — togliere il gesto, e vedere
la sezione cadere sulla prima asserzione — **è rimasta verde**: su disco arriva
`pannelli: []` lo stesso.

Il gesto è stato tolto: **un passo che non porta carico è un passo che mente.**
Al suo posto la sezione MISURA chi scrive, chiudendo prima i moduli e poi la
cartella:

```
scritture dopo i moduli : [{pannelli: 6}]
scritture dopo tutto    : [{pannelli: 6}, {pannelli: 0}]
```

Due scritture, e la seconda — quella con zero pannelli dentro — arriva con la
chiusura della **cartella**: l'unico pannello che ha un proprietario, il fondo,
e che perciò passa da `suCambio`. Non è più un ragionamento nel commento: è un
numero nel JSON, e `test_12` lo asserisce.

---

## Che cosa si è scritto

**`scripts/prova-icone.mjs`, sezione 8 `soloIlFondo`**: chiude tutti i pannelli
— cartella aperta compresa — attende oltre `RITARDO_MS = 500`, legge il disco,
riavvia una terza volta e confronta. `uguali()` è uscita dal corpo della sezione
7, perché adesso la usano in due.

**`tests/test_layout.py::test_12`**, quattro asserzioni che dicono quattro cose
diverse:

| asserzione | che cosa dimostra |
|---|---|
| `chiusura.scritture[-1].pannelli == 0` | la chiusura scrive, e l'ultima scrittura porta zero pannelli |
| `su_disco.pannelli == []` col fondo pieno | il caso è stato **prodotto**, non descritto |
| `ripristino.ricevuti == 0` | quel layout è arrivato al renderer, che ha attraversato la guardia **dal fondo** |
| `icone_uguali` | la proprietà di §26.5 vale |

---

## Le misure

```
                        PRIMA (HEAD)              DOPO
sezione soloIlFondo     non esiste                esiste
ricevuti                7  (dai pannelli)         0  (dal fondo)
su_disco.pannelli       —                         []  con 9 icone e 1 cartella
icone_uguali            —                         True
```

---

## La bocciatura ① — eseguita, sul disegno finale

In copia scratch, `ui/src/app.js` senza `+ suoFondo`:

```
VERDE  test_10_riavviato_il_core_e_ANCORA_LI
VERDE  test_11_una_cartella_aperta_si_riapre
ROSSO  test_12_un_layout_di_SOLE_icone_si_rimette
       il renderer non ha ripristinato NIENTE: con `pannelli: []` la
       guardia di §26.5 e' tornata indietro, e il fondo e' andato perso
```

Sotto la perturbazione `suoFondo > 0` salta `icone.posa()` e `roba == 0` ritorna
subito: il fondo resta vuoto, e `window.__layout.ripristino` non viene mai
scritto. Il `?? null` nella sezione serve a questo — senza, la prova cadrebbe
con un `KeyError` invece che con la propria asserzione, e un rosso illeggibile è
un rosso peggiore.

---

## L'intermittenza di `TestIconeVere`: adesso ha una diagnosi

Il 29 agosto era misurata 1 su 6 e **non diagnosticata**. Dodici corse oggi, sei
per versione, giudicate con le asserzioni vere:

```
                                         HEAD          disegno finale
test_1 … test_9, test_11                 0 rossi / 6   0 rossi / 6
test_10  riavviato il core e ANCORA LI   3 rossi / 6   0 rossi / 6
test_12  un layout di SOLE icone         non esiste    0 rossi / 6
```

⚠️ **Sei corse non bastano a dire «risolto», e questo turno non ha toccato
niente che possa averlo risolto.** Il difetto sta a HEAD, con la sua firma; sul
disegno finale non si è ripresentato in sei corse. Sono due fatti, non una cura.
(Le due corse sotto `pytest` fatte prima della bocciatura ② — quando la sezione
aveva ancora il gesto sul fondo — hanno visto rossi anche `test_1`, `test_2` e
`test_9`: un gesto in più era una sorgente in più di assestamento.)

**La firma di `test_10` è sempre la stessa**: `rimozione.tolta: True` — `agenti`
viene tolta — e al riavvio torna, nove icone prima della chiusura e dieci dopo.
È parola per parola il guasto che il commento in `ui/src/app.js` dà per risolto.

> ⚠️ **CORRETTO il 30 agosto 2026, poche ore dopo. La diagnosi qui sotto è
> FALSA, e la sua smentita è misurata.** Il flush di `pagehide` funziona: tre
> chiusure a confronto — con l'attesa, con `app.close()` di Playwright, con
> `BrowserWindow.close()` vera — hanno recapitato il marcatore **tutt'e tre**.
> Cercandone la causa vera si è trovato un difetto **diverso** — il layout
> trattenuto dal freno del core e perso alla chiusura della scrivania — che è
> stato chiuso in `docs/acceptance/L-ULTIMA-MODIFICA-PRIMA-DI-CHIUDERE.md`.
> ⚠️ **Ma non è la causa di questo sintomo**: in diciotto chiusure di scrivania
> il freno non aveva mai trattenuto niente. La causa di `agenti` che torna
> **resta aperta**; due ipotesi sono eliminate.
>
> Il paragrafo resta perché sbagliare una diagnosi e cancellarla è il modo di
> rifarla domani.

**La causa è una corsa, e questa volta ha un nome.** La sezione 6 finisce con
`dorme(400)`; il debounce della persistenza è **500 ms**; la sezione 7 chiude
l'app subito dopo. Il flush esiste — `window.addEventListener("pagehide", () =>
persistenza.adesso())` in `ui/src/app.js` — ma `salvaLayout` è asincrono, e
sotto `app.close()` di Playwright non sempre arriva a destinazione.

⚠️ **Non corretta in questo turno, e dichiarata.** La cura dipende da quale
delle due cose si sta guardando, e non è una riga da infilare in un turno che ne
fa un'altra:

- se è un artefatto della prova, si aspetta oltre il debounce prima di chiudere;
- se è del prodotto — un cambiamento fatto negli ultimi 500 ms prima di uscire
  che si perde — allora `pagehide` non basta, e la cura sta altrove.

Distinguerle vuol dire misurare se il flush arriva al core quando la finestra si
chiude davvero, e non sotto Playwright. È un turno suo.

---

## Che cosa resta NON MISURABILE

**L'ultimo centimetro**, come già dichiarato il 29 agosto: la sezione legge
`icone.stato()` e il DOM, non lo schermo. Che il messaggio `ui.layout` diventi
pixel è letto nel codice, non visto.
