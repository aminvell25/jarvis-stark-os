# I pannelli fuori scena — la classifica, e dove la leva finisce

> Dopo il globo, la domanda era: quali altri pannelli hanno lo stesso difetto?
> Misurati **tutti e 27** i componenti della galleria, non scelti a occhio.

---

## Il metodo

Uno scatto per componente (`node scripts/shot.mjs all`), poi per ciascuno la
scomposizione in bande **scartando lo sfondo della galleria** — i pixel sotto
L 22, che sono il vuoto attorno al pannello e falserebbero ogni riga.

Ordinati per la banda **25–60**, quella del corpo nudo:

| componente | lum | H | L<25 | **25–60** | 60–120 | >120 |
|---|---|---|---|---|---|---|
| ciambella | 58,6 | **1,29** | 0 | **77,7** | 12,5 | 9,8 |
| tabella | 55,3 | 2,35 | 0 | 74,8 | 15,2 | 10,0 |
| **meteo** | 46,5 | 1,88 | 0 | **73,4** | 23,3 | 3,3 |
| chrome | 55,1 | 2,53 | 0 | 66,2 | 26,7 | 7,1 |
| dials | 77,6 | 2,18 | 1,6 | 63,5 | 14,9 | 20,0 |
| budget | 73,4 | 2,92 | 4,6 | 60,8 | 15,1 | 19,5 |
| … | | | | | | |
| calendario | 67,8 | 2,20 | 0 | **33,2** | **63,4** | 3,5 |

`calendario` sta in fondo alla classifica ed è il pannello che §10.5 ha usato
come modello: il 63,4 % nella banda dei riempimenti. È la prova che la classifica
misura la cosa giusta.

---

## Che cosa è stato fatto: meteo

Sette colonne, ognuna con un massimo e un minimo. **Un'escursione è un
intervallo, e un intervallo si disegna.**

Due numeri incolonnati dicono «29» e «19». Una barra dice quanto è ampia la
giornata **e dove sta rispetto alle altre** — la stessa informazione più il
confronto, che i numeri da soli non danno.

La scala è quella della **settimana intera**: senza, ogni colonna userebbe la
propria e le barre non sarebbero confrontabili, che è il solo motivo per cui una
barra esiste. Un decimo di margine sopra e sotto, perché una barra che tocca il
bordo si legge come un limite e non come un valore.

`--fill-2` (L 89), e `--fill-3` sul giorno corrente — **la prima volta che
`--fill-3` viene usato da un componente**, che `TOKENS-RIEMPIMENTO.md` segnalava
come mai accaduto.

| | prima | dopo |
|---|---|---|
| entropia | 1,88 | **1,97** |
| L 25–60 | 73,4 % | **72,1 %** |
| L 60–120 | 23,3 % | **24,6 %** |

Audit `meteo` **0/0**, suite **564 passed**.

---

## ⚠️ Dove la leva finisce, e perché mi sono fermato

Gli altri pannelli in cima alla classifica **non hanno lo stesso difetto**, e
guardarli lo dice meglio dei numeri:

- **`dials`** — i quadranti sono già strumenti: archi pieni a `--cy-500`, scale
  incise, ago rosso. Il loro 63,5 % è **corpo di pannello attorno a tre
  quadranti piccoli**, non dato mancante. Ingrandirli è composizione, non dato.
- **`ciambella`** — la ciambella dice già le quote, e la legenda porta nome, kB
  e percentuale. Una barra dietro le righe sarebbe la **terza** codifica dello
  stesso numero.
- **`tabella`** — è la ricetta: la sua zebra è `--bg-panel` *per scelta*, «sei
  punti di L, non un colore». Alzarla la romperebbe.

Il divario che resta in quei pannelli è **superficie di corpo non coperta da
contenuto**, e si chiude con più dato, non con più colore. Metterci un
riempimento perché il numero salga sarebbe la decorazione che riempie che §11.6
regola 2 vieta — ed è la stessa conclusione a cui è arrivata la Fase 2 sulla
scrivania.

---

## Che cosa NON è stato verificato

- **La classifica è su scatti di galleria**, dove ogni componente ha la propria
  fixture e la propria dimensione: confronta la *proporzione* fra bande, non le
  superfici assolute.
- **I «-dettaglio»** (agents, news, periodic, browser, planes, board, glyphs,
  rings, gestures) sono ritagli con molto vuoto attorno: il loro `L<25` alto è
  cornice della galleria, non pannello. Restano nella tabella per completezza,
  non per il giudizio.
> ### ✅ `chrome` e `budget`, guardati — e nessuno dei due è un pannello
>
> Erano l'ultima voce aperta di questo documento. Aperti:
>
> - **`chrome`** è la **fixture dell'ambiente**: barra, catalogo, dock e le
>   cartelle manila libere sul piano — che rendono correttamente, e sono la
>   prova che `desk/icone.js` sa disegnarle. Il suo 66,2 % è **scrivania
>   vuota**, non corpo di pannello;
> - **`budget`** è il **banco del budget di frame**, tre pannelli affiancati per
>   misurare §10.4. Il suo 60,8 % sono tre corpi, non uno.
>
> Nessuno dei due appartiene a una classifica di pannelli: la classifica misura
> la proporzione fra bande su ciò che è inquadrato, e su una fixture inquadra
> soprattutto il vuoto.
>
> ⚠️ E aprire `budget` ha trovato un difetto vero — vedi sotto.


---

## ⚠️ Il banco stampava un verdetto che non poteva emettere

`shots/budget.png` riportava:

```
frame 83.30 ms · p95 100.10 · tetto 16.7 · SFORA
```

Il banco **vero** — `npm run bench`, che gira nella finestra Electron con la GPU
vera — dice:

```
three 0,70 / 8,0    pixi 0,60 / 3,0    anime 0,00 / 4,0    frame 16,70 / 16,7
```

Tutto dentro. Chi leggesse quello scatto concluderebbe che il budget è sfondato
di cinque volte, e che la sfera del globo l'ha rotto.

**La causa.** I tetti di §10.4 sono **quote di un fotogramma da 16,7 ms**:
three.js 8, Pixi 3, anime.js 4. Se il fotogramma intero non sta a 16,7 — perché
la pagina non è su uno schermo che si aggiorna, per esempio sotto Playwright
durante uno scatto — quelle quote non sono superate: sono **non misurate**. E
stamparci sopra «SFORA» è dire una cosa falsa con l'aria di un dato.

**Il rimedio** non è un elenco di ambienti da riconoscere, che invecchierebbe:
è la condizione che rende la misura possibile. Se il fotogramma intero è almeno
**il doppio** del proprio tetto, la pagina non gira a vsync e nessuna quota di
quel fotogramma significa niente — il verdetto diventa «non misurabile», la riga
non si accende in rosso, e l'intestazione dice dove sta il banco vero.

Il numero **resta stampato**: nasconderlo sarebbe l'errore opposto.
