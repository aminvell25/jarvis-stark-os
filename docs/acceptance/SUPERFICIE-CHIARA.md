# La superficie chiara — dev.std passa, l'entropia resta aperta

**Data:** 23 agosto 2026
**Rollback:** `30fb82e`
**Precedente:** `ISTOGRAMMA-E-BIN-VUOTI.md`

## Che cosa doveva fare questo turno

L'istogramma aveva stabilito che i token chiari sono **tutti inchiostro, mai
superficie**, e che la dev.std si compra con la distanza dalla media: `--icona`
(L 171) rende **+2,18 per 1 %** di area, `--cy-900` (L 48) **+0,00**. Restavano
sotto soglia entropia (2,17 < 2,40) e dev.std (31,3 < 32).

Il piano: rendere superficie ciò che era tratto, correggendo **due difetti che
il codice stesso dichiarava e aveva rinviato**, e dichiarare aperta l'entropia
invece di aggiustarla.

## Esito misurato

**Tre esecuzioni indipendenti**, non un campione — la lezione dell'errore
`L>60 25,2 %` di stamattina:

| | prima | run 1 | run 2 | run 3 | soglia |
|---|---|---|---|---|---|
| **dev.std** | 31,3 | **32,9** | **33,0** | **32,95** | 32 ✅ |
| entropia | 2,17 | 2,20 | 2,20 | 2,20 | 2,40 ❌ **aperta** |
| L>60 | 25,0 % | 26,3 % | 26,3 % | 26,3 % | 25 ✅ |
| L>120 | 4,6 % | 5,1 % | 5,1 % | 5,1 % | — |
| caldo | 3,8 % | 3,8 % | 3,8 % | 3,8 % | 3–6 ✅ |
| bin sotto lo 0,5 % | 9 su 16 | 9 su 16 | | | — ❌ |

Lo scarto fra le tre è **0,1** sulla dev.std e **zero** su tutto il resto: il
32,9 non è un campione fortunato.

`npm run verifica:scrivania` **exit 0**. `node scripts/audit.mjs chrome
telemetry` **0/0**.

## I tre passi

### 1. `telemetry.js` — il processo più pesante prende `--fill-3`

Le tre righe di `top3` avevano tutte la quota a `--fill-2`, e la più pesante si
distingueva solo per lunghezza: fra 21 % e 19 % sono due barre quasi uguali, e
*quale sia il primo* è l'informazione per cui si guarda quell'elenco.
`tokens.css` definisce `--fill-3` «evidenza dentro una griglia densa».

Il massimo lo **misura il componente** (`Math.max` sui `cpu`), non lo deduce
dall'ordine di arrivo: `core/platform/linux.py:212` ordina già, ma un secondo
lettore che dipende da quell'ordine è un secondo posto da cui rompere la stessa
cosa. E si accende solo se il massimo è **> 0**: con tutti i processi a zero non
esiste un «più pesante», e accenderne uno direbbe il falso.

⚠️ **Da solo questo passo abbassa l'entropia**, perché svuota un bin per
riempirne un altro. Si è fatto per l'informazione, non per la metrica.

⚠️ **Costo dichiarato**: `--txt-primary` su `--fill-3` misura **4,54:1** contro
i 5,44:1 su `--fill-2`. Resta sopra il 4,5 di AA, con **0,04** di margine, e
riguarda solo i caratteri che la barra copre.

### 2. `catalogo.js` — le tessere alla dimensione dichiarata

Da **20×20 a 48×32**. Il file dichiarava da giorni che i 20 px erano sbagliati:
«28×14 px» è misurato su un pannello largo 342 in un'immagine larga 901, e il
numero da trasferire è la **frazione** — 8,2 % della larghezza, che sui nostri
605 fa 50. E il rettangolo 2:1 era diventato un quadrato: due errori nella
stessa riga. Dalla scala: `--s-4 + --s-3` × `--s-4`, rapporto 1,5:1 contro
l'1,52:1 del riferimento. Il glifo passa da `--s-3` a `--s-3 + --s-2` (24 px).

### 3. `catalogo.js` — la piastra del plinto

Da **32 a 64 px**, e con lei `PASSO` 52→104, `APERTURA` 16 (invariata) e `FUGA`
26→52. Il lato vive adesso in **un posto solo**, `--piastra` su `.cat`, perché è
anche il ritaglio della scena, il centraggio della piastra e lo sbalzo sulla
griglia.

⚠️ **64 e non 68.** La frazione (4,4 % di 1536) darebbe 68, ma 68 non è nella
scala e la sua metà non è multiplo di 4: **l'audit di §11.8 l'ha bocciato**
(`margin-left: -34px`). `--s-5` vale il 4,17 % contro il 4,4 % misurato — 0,23
punti di scarto, contro i 2,3 che i 32 px lasciavano aperti.

⚠️ **E cinque piastre da 64 non ci stanno.** È aritmetica: `.cat__scena` misura
**316 px** e cinque piastre larghe 72 ne vorrebbero 360. `FINESTRA` scende da 5
a 3. Cede «cinque» e non il lato, perché i cinque venivano da un **conteggio**
delle icone del riferimento mentre il lato viene da una **frazione** della sua
larghezza — e `design-reference/README.md` dice che si trasferisce la frazione.
Tre piastre a passo 104 coprono 280 px su 316: l'**89 %** della lastra contro il
75 % di prima.

Chi rivolesse le cinque allarghi `.cat`: il catalogo del riferimento è 342 su
901, il **38 %** della larghezza, e il nostro è il **27,6 %**. È una decisione
sul pavimento della scrivania, non su quella riga.

## Che cosa il ciclo §11.7 ha trovato, e che a occhio non si sarebbe visto

Il primo rendering con la piastra a 64 px era **rotto in due modi**, e tutti e
due si sono visti solo guardando lo scatto:

1. **Le piastre coprivano la seconda riga di tessere**, 25 px di
   sovrapposizione. Il margine che serve a impedirlo esisteva già — `.cat__vista
   { margin-bottom }` — ma era scritto `--s-4 + --s-1`, cioè con la misura della
   piastra **copiata** invece che riferita. Alzata la piastra, il margine è
   rimasto a 36. Adesso legge `--piastra`: una verità sola, e la prossima volta
   si muovono insieme. Il commento sopra quella riga descriveva **già** questo
   identico difetto, capitato una prima volta.
2. **Le due piastre esterne uscivano tagliate di 14 px** dal ritaglio della
   scena, perché avevo scalato `APERTURA` a 32 come tutto il resto. Il vincolo
   non è la proporzione, è il ritaglio: 104 + 32 + 36 = 172 contro i 158 di
   mezza scena. `APERTURA` resta 16 — 104 + 16 + 36 = 156.

## Il modello ha sbagliato la magnitudine, e il verso no

Le proiezioni di `ISTOGRAMMA-E-BIN-VUOTI.md` davano **dev.std 35–37**. Misurata:
**32,9**. Il verso era giusto (+1,6 contro un fabbisogno di +0,7), la quantità
no, di circa cinque volte.

**Perché.** Il modello tratta l'area aggiunta come un blocco pieno a **una**
luminanza. La piastra non lo è: è un **gradiente** da `--icona-viva` (219) a
`--icona` (171), quindi i suoi pixel si spargono su quattro bin invece di
cadere in uno; porta dentro un **glifo scuro** a `--bg-void`, che le toglie
circa un terzo dell'area; e la **prospettiva** rimpicciolisce le due piastre
laterali. Bin 10–13 sommati passano da 0,6 % a 0,9 %: **+0,3 %**, non l'1,07 %
che la geometria prometteva.

**Criterio 4 del piano — «i bin 10 e 13 escono dallo 0,5 %» — è FALLITO**:
stanno a 0,2 % e 0,3 %. I bin sotto lo 0,5 % restano **nove su sedici**.

La regola che ne esce, per chi userà quel modello: **una superficie con un
gradiente, o con un contenuto scuro dentro, vale una frazione della propria
area geometrica.** Si misura, non si deriva.

## L'entropia — non chiusa, e perché

**2,20 su 2,40.** Non è stata aggiustata e non si è aperto nessun cancello.

Tutto ciò che è risultato legittimo nella scena — con `meteo` portato dentro —
arriva a **2,343** per calcolo. L'unico bin che chiude il divario è lo **0**
(L 0–15), dove stiamo a **0,0 %** e il riferimento a **5,2 %**, e sotto L 19 non
esiste alcun token. Aggiungerne uno è un cancello di governance separato, come
`e4851ae`; abbassare `--bg-void` sotto L 16 contraddirebbe una misura del
riferimento e l'avvertimento esplicito di §10.1 sul «sistemare» la rampa.

Decisione del proprietario: **si fa il raggiungibile, l'entropia si dichiara
aperta.**

## Il bin 3 è uscito dal piano, e non serve alcun cancello

Il piano precedente proponeva il 6–8 % del fotogramma a `--cy-900` (L 48). Due
ragioni indipendenti l'hanno escluso:

1. **Non compra dev.std**: dista 8 punti dalla media (L 47,7) e rende +0,00 per
   1 %; con l'area presa dal pavimento la **abbassa**.
2. `--cy-900` è il riempimento delle fasce del nucleo (§25.5, `e4851ae`), e il
   nucleo sta **sotto** i pannelli: lo stesso token sui due ridurrebbe il
   confine a un gradino di alfa.

Nessun token nuovo è stato dichiarato in questo turno.

## Un difetto ripetuto, e la regola procedurale che ne segue

Un **backtick dentro un commento CSS** ha chiuso il template literal di
`catalogo.js` per la sedicesima volta. `tests/test_fogli_di_stile.py` lo prende
— verificato reinserendolo apposta, e il test nomina file e token:

```
assert not ['  ui/src/desk/catalogo.js · css · `--piastra`']
```

Ma io non l'ho consultato: me ne sono accorto dallo scatto andato in timeout
dopo 120 secondi. **La regola non è "non scrivere backtick", è: dopo ogni
modifica a un blocco `css`, si lancia quel test PRIMA dello scatto.** Costa
0,05 s contro i 90 dello scatto.

## Limiti dichiarati

- **Il margine della dev.std è 0,9–1,0**, non i 5,1 previsti. È sopra soglia in
  tre esecuzioni su tre, ma resta un margine sottile — la stessa forma di
  fragilità che questo ciclo di lavoro sta correggendo altrove.
- **`prova-catalogo.mjs` non ha esercitato la griglia**: apre la linguetta FILE,
  che senza attività su disco è vuota (`tessere: 0`). Lo scorrimento a inerzia
  con le tessere nuove **non è stato verificato**. Il budget di frame sì:
  mediana 16,7 ms, max 17,1.
- **Il catalogo copre più pavimento di prima**: `.cat` è cresciuto di 32 px in
  altezza — da 191 a 223 — per fare posto allo sbalzo delle piastre. Misurato:
  il pavimento coperto **dalla cornice** passa da **7,1 % a 8,2 %**, e il libero
  da 29,6 % a 29,0 %. Sono 1,1 punti che vanno al catalogo e non al globo, che
  è il pannello sotto. Non è una regressione della densità — la cornice è
  superficie anche lei — ma è un pannello che si vede un po' meno.
