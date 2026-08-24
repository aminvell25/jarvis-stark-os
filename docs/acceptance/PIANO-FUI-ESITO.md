# Il piano per la FUI avanzata — esito, fase per fase

**Data:** 24 agosto 2026 · **Piano:** otto fasi, ~15 giorni dichiarati

| fase | esito | dove |
|---|---|---|
| 0 · il cancello §10.6 | ✅ **fatto** — tre classi di moto, §11.7 regola 4 | `CANCELLO-10.6.md`, `500b9ef` |
| 0 · il banco | ✅ **fatto** — dock 2,0 %, cinque pannelli che debordano, budget per motore | `FASE-0-IL-BANCO.md`, `0a07541` |
| 1 · pannelli che si contraggono | ✅ **fatto**, e la parte sulla scena **ritirata dopo la misura** | `FASE-1-CONTRAZIONE.md`, `4a273ca` |
| 2 · colonna laterale | ❌ **non entra** — è una somma, non una difficoltà | `FASE-2-COLONNA-NON-ENTRA.md`, `2e6d640` |
| 3 · apertura del pannello | ✅ **fatto** — 180 ms, e il rischio peggiore non si è avverato | `FASE-3-APERTURA.md`, `4ef1912` |
| 4 · boot disegnato | ❌ **non fatto** — vedi sotto |  |
| 5 · giro §11.7 sui 18 | ❌ **non fatto** — vedi sotto |  |
| 6 · equalizzatore vocale | ❌ **non fatto** — vedi sotto |  |
| 7 · `<webview>` viva | ❌ **non fatto** — vedi sotto |  |
| 8 · API anime.js | ❌ **declinata**, con la ragione |  |

Tre fasi costruite, una dichiarata impossibile con l'aritmetica, quattro non
fatte. Sotto c'è il perché di ciascuna, e che cosa serve a chi la riprende.

---

## Fase 4 — il boot disegnato

§10.4 prescrive `svg.createDrawable()` + `createTimeline()`. **Il nucleo non ha
tratti da disegnare**: da `e4851ae` le sue fasce sono **riempimenti**, non
contorni — la scala di §25.5 è salita e il tratto è diventato superficie.
`createDrawable` lavora su `stroke-dasharray`, e su una forma piena non ha
niente su cui lavorare.

E il criterio che il piano stesso poneva — *«si avvia contro un core freddo e
contro un core caldo: le due durate devono differire, altrimenti è teatro»* —
richiede che ogni anello si disegni **quando la sua fase arriva**. `sfondo.js`
espone `ins.fase()` e anima l'opacità per fase, ma non un aggancio «disegnati
adesso» per gruppo.

**Serve**: che il nucleo esponga un aggancio di disegno per anello, o che il
boot disegni qualcos'altro di stroked che stia a schermo — i cavi della mesh in
`agents.js` sono l'unico candidato.

⚠️ E il piano lo dichiarava già: **resa percepita massima, resa misurata ZERO**.
Il protocollo scatta a T+3 s e un boot da 1,8 s lì non esiste.

---

## Fase 5 — il giro §11.7 sui 18 componenti

Dichiarato in tre documenti come **«l'80 % del divario visivo»**. La premessa
non regge come scritta: **i componenti a schermo nella scena `avvio` sono
SEI**, non diciotto. Gli altri dodici stanno nel catalogo, e un componente che
non è a schermo non muove nessuna metrica di densità.

Misurata la mossa più redditizia che resta fra i sei — l'emisfero illuminato del
globo da `--fill-1` (bin 4, affollato al 13,8 %) a `--fill-2` (bin 5, all'1,6 %),
3,7 % del fotogramma:

```
oggi                          H 2,188   dev 33,4
emisfero bin 4 -> bin 5       H 2,257   dev 34,0     +0,07
```

**+0,07 su +0,21 necessari**, e in cambio si contraddice un commento di
`globe.js` che dice per esteso perché quei due colori sono *«un fondo»* e non
*«un colore del dato»*. Un colore che smette di significare per far salire una
metrica è §11.6 regola 2 violata alla lettera.

⚠️ **È la terza volta che la stessa misura dice la stessa cosa** — dopo
`ENTROPIA-AREA-CHE-NON-CE.md` e `FONDO-26-5.md`. La conclusione non cambia:
*le superfici chiare vogliono stati, e a scrivania ferma gli stati non
accadono*. Rifare l'esperimento una quarta volta sarebbe spreco.

**Serve**: più contenuto a schermo, non più colore. Le due strade sono la scena
(più pannelli composti insieme) e le sorgenti vive del cancello §10.6.

---

## Fase 6 — l'equalizzatore vocale

Il cancello §10.6 è aperto **apposta per questo**, e la fase resta non fatta
perché il lavoro non è nell'interfaccia:

- `core/voice/audio_io.py` è da **zero byte**, ed è la cattura del microfono che
  `pipeline.py` presuppone;
- serve un topic nuovo, che **nessun documento prescrive** — §11.5 prescrive il
  componente, non il trasporto;
- `config/settings.toml` ha `voice.enabled` da accendere.

⚠️ **Accendere un microfono è una decisione, non una rifinitura**, e non la
prendo dentro un turno di implementazione.

**Il dato minimo onesto esiste già**: `core/voice/pipeline.py` calcola
`VAD.energia(pcm)`, RMS per blocco, sul percorso caldo. Si pubblica quello. Una
FFT a bande **solo se una sonda mostra che serve**, non perché il riferimento ha
sedici barre.

---

## Fase 7 — la `<webview>` viva

Il piano metteva **la sonda prima della costruzione**, e ha ragione: il
precedente esatto è `ISTOGRAMMA-E-BIN-VUOTI.md`, che ha misurato il modulo Media
prima di scrivere codice e ha trovato che peggiorava due metriche su due.

La sonda vuole **una pagina viva**, cioè rete e un sito scelto. E il rischio non
è di codice ma di **policy**: una pagina viva è contenuto `Untrusted`
(invariante 5), e passa dall'essere presente *su richiesta* a essere presente
*all'avvio*, senza che un umano l'abbia chiesta.

⚠️ **È una riga di decisione del proprietario**, e va presa prima della sonda,
non dopo.

---

## Fase 8 — le API anime.js

Il piano la dava **facoltativa**. Declinata, e la ragione è la stessa che
l'invariante 25 esiste per dire:

| API | perché no |
|---|---|
| `createSpring` | sostituirebbe l'inerzia scritta a mano di `catalogo.js`. Cambia un **gesto misurato** con una guardia che passa (`verifica:catalogo`, sei condizioni), in cambio di codice più corto. Rischio reale, valore nullo |
| `createTimer` | un orologio che batte al secondo. **Nessun consumatore**: nessun componente chiede l'ora al secondo |
| `onScroll` | il catalogo scorre già, con la propria inerzia provata e asserita |
| ~~`splitText`, `scrambleText`~~ | **rifiutate**: un valore che arriva carattere per carattere racconta una gradualità che non è successa. Dato finto travestito da movimento — invariante 23 prima ancora della 25 |

---

## Dove sono le soglie, alla fine

| | oggi | soglia | |
|---|---|---|---|
| dev.std | 34,1 | 32 | ✅ margine +2,1 |
| `L>60` | 25,6 % | 25 | ✅ margine +0,6 |
| caldo | 3,8 % | 3–6 | ✅ |
| barra | 63,3 % | 25 | ✅ |
| **entropia** | **2,23** | **2,40** | ❌ **aperta** |
| dock | 2,0 % | 20 | ❌ in rapporto, non boccia |

Suite **572 verdi**. `verifica:scrivania`, `verifica:catalogo`,
`verifica:contrazione`: tutte exit 0.

## Che cosa ha prodotto davvero questo piano

Non l'entropia. Ha prodotto **misure che prima non esistevano** — il dock, le
risoluzioni, il budget per motore — e con esse due difetti che nessuno vedeva:
cinque pannelli che debordano alla risoluzione su cui misuriamo da sempre, e un
`debordaX` raccolto da mesi senza entrare in nessun verdetto.

E una regola: **§11.7 regola 4**, che in due giorni si è applicata tre volte.
