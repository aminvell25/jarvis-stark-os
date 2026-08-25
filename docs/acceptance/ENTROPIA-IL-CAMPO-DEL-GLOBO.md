# Il campo del globo era dipinto col colore del suo telaio

**Rollback:** `c3f42e3`
**Criterio:** entropia dell'istogramma a 16 bin ≥ 2,40 bit
**Esito: NON SODDISFATTO — 2,394. Il divario è passato da 0,197 a 0,006.**

---

## 1. Come si trova un difetto guardando una metrica

`ENTROPIA-AREA-CHE-NON-CE.md` aveva concluso, il 24 agosto:

> Le superfici chiare vogliono stati, e a scrivania ferma gli stati non
> accadono.

Corretto, e **incompleto**. L'entropia è simmetrica: massa spostata in un bin
vuoto **scuro** vale quanto in uno chiaro, e il buio non chiede nessuno stato.
Nessuna delle analisi precedenti aveva guardato il bin 0.

```
 bin   L          nostro   riferimento
   0    0- 15     0.0%      5.2%      ← e nessuno l'aveva letto
   1   16- 31    36.5%       26%
   2   32- 47    36.4%     18.5%
```

Poi la domanda giusta: **dove** sta quel 5,2 % nel riferimento. Griglia 6×8 su
`famiglia-a/01`, percentuale di pixel sotto L 16 per cella:

```
    1.3   1.0   0.1   0.0   0.0   0.0   28.5   41.3
    0.1   0.5   1.0   0.1   0.0   0.0   13.5   32.4
    2.1   3.6   4.9   1.3   0.1   0.1   26.8   27.8
```

Le due colonne a destra, le tre righe in alto: **il pannello del globo e
quello della mappa**, e nient'altro. Dominante `#03080c`, L 7,2.

## 2. Il difetto, che la metrica ha solo indicato

Il campo attorno al pianeta era `--bg-raised` — **lo stesso valore della
scatola che lo contiene**. Il campo di una vista dipinto col colore del suo
telaio.

Misurato, contro il campo:

| | prima | dopo |
|---|---|---|
| emisfero in ombra `--bg-panel` | **1,08:1** | 1,22:1 |
| lembo illuminato `--fill-1` | 1,54:1 | 2,03:1 |
| `--cy-100` sul campo | 12,43:1 | 16,37:1 |

**1,08:1 è invisibile.** Il lembo in ombra spariva dentro il pannello: non si
vedeva dove finiva il pianeta.

⚠️ **1,22:1 non è un successo WCAG**, e dirlo sarebbe barare. Il rapporto WCAG
comprime al fondo della scala; la cosa che si vede è la separazione di
luminanza, passata da **6,4 a 23,1 punti**. Che il disco adesso si legga è
**guardato** in `shots/globe.png` e nel ritaglio della scrivania, non dedotto
da un numero.

### Una diagnosi mia, ritirata

Avevo scritto — nel commento del codice, nella riga di §10.1 e in un test —
che i 312 fusi notturni stavano su `--bg-raised` a **2,82:1**, sotto il 3,0
che §10.1 impone. **Falso.** Campionando lo scatto, i fusi stanno sulla sfera:
`--cy-700` su `--bg-panel`, **3,04:1**, che passa ed è la coppia che il test
già verificava. Tutti e tre i posti sono stati corretti prima di procedere.

L'errore è la specie di sempre — un numero aritmeticamente vero su una coppia
che non sta sullo schermo — ed è stato trovato **guardando lo scatto**, che è
il passo che §11.7 mette apposta prima del verdetto.

## 3. §10.5 regola 1 non è rotta: è misurata

Il corpo del pannello adesso è **sotto** il pavimento invece che sopra, e
sembra un'inversione della regola. Misurata su entrambe le immagini, la
separazione campo → scrivania:

| | |
|---|---|
| riferimento `famiglia-a/01` | **11,5 punti** |
| nostro | **11,6 punti** |

`famiglia-a` inverte il gradino sotto il globo esattamente così. La testata
resta `--fill-1` (L 66) e la cornice `--bg-raised` (L 37) contro il pavimento
(L 19): il gradino del **chrome** è intatto. Cambia il **campo**, che è
contenuto.

## 4. Il token

`--bg-abyss:#05080b` (L 7,6), **suolo di una vista, non un gradino della
rampa**. Non esisteva niente sotto L 16: il più scuro era `--bg-void` a L 19.

Il colore lo dipinge il CSS. Il renderer resta `alpha: true` come
`three/scena.js` impone, o l'invariante 18 cadrebbe proprio dove è più facile
non accorgersene.

Due asserzioni nuove in `tests/test_tokens.py`: `--bg-abyss < --bg-void`, e
`L < 16` — perché un valore a L 17 sarebbe più scuro del pavimento e
continuerebbe a non entrare nel bin 0, cioè sembrerebbe la stessa mossa senza
esserlo.

## 5. La misura, su una fixture con pavimento di rumore 0,00

| | prima | dopo |
|---|---|---|
| **entropia** | 2,2032 | **2,3940** |
| bin 0 | 0,00 % | **4,34 %** |
| dev.std | 33,99 | 34,86 |
| `L>60` | 25,1 % | 25,1 % |
| caldo | 3,8 % | 3,8 % |
| barra | 63,8 % | 63,8 % |

E l'attribuzione, che dice che non si è mosso nient'altro:

```
g1.png contro scrivania.png: 57.662 pixel (4,45 %), massimo scarto 38/255
  dentro 472x278 a (4, 410)
```

`472x278 a (4, 410)` è il campo del globo. **Il resto della scrivania è
identico byte per byte.** Un anno fa questo confronto non si sarebbe potuto
fare: è la fixture di `c15925d` che lo rende una misura invece di
un'impressione.

## 6. Perché mi fermo a 2,394 e non a 2,401

Mancano **0,0060**. Quanta area servirebbe, presa dal bin 2:

```
    bin 14  (L 224-239)   0.058 %  =   752 px  (27x27)
    bin 15  (L 240-255)   0.057 %  =   739 px  (27x27)
    bin 11  (L 176-191)   0.091 %  =  1173 px  (34x34)
```

**Un quadrato di 27 pixel di lato.** Aggiungerne uno farebbe passare la soglia
e non migliorerebbe niente: è la stessa specie di difetto che §11.7 regola 4
esiste per impedire — un numero che diventa verde senza che il fenomeno sia
cambiato.

La seconda mossa l'ho cercata e non l'ho trovata giusta:

- **il pavimento** — il riferimento ce l'ha a L 26-27, cioè dove sta il nostro:
  niente da spostare;
- **i corpi dei pannelli** (bin 2, ancora il 32 %) — §10.5 regola 1 li fissa;
- **l'emisfero notturno** a `--bg-abyss` — fisicamente allettante, ma
  cancellerebbe la silhouette che questo turno ha appena reso visibile;
- **i mezzitoni del riferimento** (bin 3 al 10,2 % contro il nostro 2,6 %) —
  vengono dalla **texture fotografica** del suo globo: oceani, nuvole,
  continenti. Il nostro è una graticola wireframe per scelta di progetto, e il
  riferimento non giustifica di cambiarla.

**L'entropia resta aperta a 2,394 su 2,40**, col numero, la ragione e la misura
di quanto manca.

## 7. Verifica

| | |
|---|---|
| `npm run shot -- globe` | audit 0 elementi fuori sistema, 0 letterali · esito OK |
| checklist §11.8 | nessun ✗ — punto per punto in §8 |
| `npm run scrivania:fixture` | EXIT=0, `scattiIdentici` true |
| `uv run pytest -q` | **585 passed** |
| `npm run verifica:marchio` | §25.13.5 soddisfatto in tutti gli stati |
| `npm run verifica:catalogo` | §26.9 criterio 3 soddisfatto, 6 condizioni su 6 |
| `docs/SPEC.md` §10.1 e `tokens.css` | byte a byte, rev 5.23 con riga di emendamento |

## 8. §11.8, punto per punto

```
GEOMETRIA
✓ border-radius 0 — non toccato
✓ taglio a 45° su 1 vertice — non toccato
✓ spaziature multiple di 4 — non toccate
✓ pesi di linea hair/base/bold — non toccati
COLORE
✓ tutti da tokens.css — audit pulito, e --bg-abyss è un token
✓ accento caldo 3,8 % < 10 %
✓ tinte ≤ 3 — --bg-abyss è la stessa famiglia fredda di --bg-void
✓ zero gradienti
✓ ZERO alone, bloom, glow — il campo è piatto
✓ nessuna ombra aggiunta
TIPOGRAFIA
✓ non toccata
CONTENUTO
✓ dati veri — i 312 fusi vengono da geo.timezones del core
✓ etichetta GLOBO TATTICO + GLB_G07 · ver 1 + piede con UTC e subsolare
✓ valori numerici in --font-mono
✓ densità: entropia 2,203 → 2,394, bin 0 da 0,00 % a 4,34 % contro il 5,15 %
   del riferimento
MOVIMENTO
✓ non toccato — nessuna animazione aggiunta
TECNOLOGIA
✓ le etichette restano DOM (.pnl-glb__nome), non rasterizzate
✓ Line2/LineMaterial — non toccato
✓ il campo lo dipinge il CSS, non WebGL
```

## 9. Dichiarato aperto

- **Entropia 2,394 su 2,40**, divario 0,006 = 739 px.
- **Bin 14 e 15 sono a 0,00 %** contro 0,7 % e 1,9 % del riferimento: la
  scrivania non ha **nessuna** superficie sopra L 224. È un fatto, non una
  proposta.
- **Bin 3 al 2,6 % contro 10,2 %**: il divario relativo più grande che resta, e
  viene dalla texture del globo del riferimento.
- **Dock al 2,0 % contro 20.** In rapporto, non blocca.
- La misura vale per la registrazione `4d5edf35cfdb64af`. Rifarla azzera la
  baseline (§11.9).

---

Le due guardie di freschezza — marchio e catalogo — sono cadute durante il
turno perche' `tokens.css` sta nelle loro `FONTI`. Hanno detto quale comando
lanciare, e dopo la rimisura sono verdi. E' il loro mestiere: un esito vecchio
sembra una verifica.
