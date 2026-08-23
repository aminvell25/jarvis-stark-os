# Le fasce chiare — l'alternanza del riferimento, e una regola che ho sbagliato

> Implementazione del cancello `docs/acceptance/CANCELLO-25.5-RIEMPIMENTO.md`.

---

## Applicato

| | prima | dopo |
|---|---|---|
| riempimento delle fasce **0, 2, 3** | `--cy-900` (L 48,5) | **`--cy-700`** (L 100) |
| riempimento delle fasce **1, 4** | `--cy-900` | **`--cy-900`** |
| tacche sulle fasce chiare | `--cy-700` | **`--cy-900`** — invertite |
| contorno delle fasce chiare | `--cy-700` (invisibile sul proprio riempimento) | **`--cy-900`** |

Quali fasce salgono lo dice la misura, non la composizione: allineando ogni
fascia al profilo del riferimento nella stessa posizione radiale, lì misura
**91,7 · 46,8 · 87,4 · 111,9 · 52,1** dall'esterno al mozzo. Tre chiare, due
scure. Il campo `chiara` sta in `ANELLI`; il **colore** lo dichiara chi monta,
perché un pannello e uno strato di presenza hanno due scale diverse.

## Il profilo, contro il riferimento

| frazione del raggio | riferimento | prima | **dopo** |
|---|---|---|---|
| 0,33–0,47 | 38,9 | 36,7 | **36,7** |
| 0,48–0,54 | **132,7** | 52,3 | **83,0** |
| 0,55–0,61 | 84,1 | 50,5 | **88,6** |
| 0,62–0,73 | **107,2** | 50,8 | **91,7** |
| 0,74–0,86 | 45,4 | 52,0 | **60,5** |
| 0,87–0,98 | **92,8** | 51,7 | **85,9** |

Per fascia nostra: **79,8 · 50,4 · 90,9 · 88,3 · 58,6**. L'alternanza c'è.

**Escursione fra la zona più chiara e la più scura: riferimento 93,8, noi 55,0.**
La differenza è quasi tutta la sua zona di picco a 132,7, che è **bloom** —
vietato dall'invariante 19 a prescindere da §25.5.

---

## ⚠️ Una regola che avevo scritto un'ora prima, e che era sbagliata

Il cancello di questa mattina aggiungeva a §25.5:

> **Su una fascia riempita sopra L 48 il tratto non porta dettaglio.** […]
> guardato a 9× sul riferimento, le sue fasce chiare sono superfici lisce e
> tutto il dettaglio radiale sta sulle fasce scure.

**Era una sola inquadratura.** Quel ritaglio mostrava il *corpo* delle fasce
chiare, che in effetti è liscio. Un secondo ritaglio, in un altro punto del
disco, mostra il dettaglio al loro **bordo interno** — che è esattamente dove
`ReactorRing` disegna le proprie tacche.

Reso senza tacche e **guardato**: il nucleo perdeva il dettaglio su **tre fasce
su cinque** e leggeva come un disco pieno. Con le tacche invertite a `--cy-900`
legge come uno strumento.

La riga di §25.5 è corretta in *«il dettaglio si **inverte**, non sparisce»*, e
la prima stesura resta scritta nel cancello — **il difetto era il metodo, non il
numero**: una misura fatta su un solo punto di un'immagine non è una misura.

---

## Le sette verifiche del piano

| # | | atteso | misurato |
|---|---|---|---|
| 1 | **il marchio, §25.13.5** | invariato a 3,04:1 | **3,04:1** ✅ |
| 2 | la densità, `L>60` | ~13,8 % | **12,5 %** (da 10,1) |
| 3 | il profilo | chiare ~100, scure < 55 | 79,8–90,9 / 50,4–58,6 |
| 4 | invariante 25 e §25.6 | `[0, 0]`, una causa per anello | ✅ |
| 5 | il pannello non cambia | audit 0/0 | **0/0**, e guardato: identico |
| 6 | il giro §11.7 | sette scatti guardati | ✅ |
| 7 | la suite | 561 | **561** |

**Il punto 1 era quello che poteva rompersi, e non si è mosso di un
centesimo.** Il nome è legato a `rCampo` — il bordo interno dell'anello 4, che
resta **scuro** — quindi il composito sotto di lui è ancora `--bg-panel` esatto.
Il legame introdotto due commit fa ha fatto il proprio lavoro alla prima prova
vera.

**Il punto 2 ha sbagliato la stima, non la direzione**: avevo previsto ~13,8 %,
misurato 12,5 %. La stima trattava le fasce chiare come piene al 100 % della
loro area, e i varchi non lo sono. Resta il salto più grande che questo nucleo
abbia prodotto: `L>60` **10,1 → 12,5 %**, dev.std **20,25 → 22,6**, entropia
**1,74 → 1,76**.

---

## Che cosa NON è stato verificato

- **La zona «media» del riferimento a L 84** non ha un gradino nostro: fra
  `--cy-900` e `--cy-700` la rampa fredda non ne ha. `--cy-800` e `--cy-600`
  sono P1/P2 di `DIVARIO-PREMIUM.md`, mai scritti. Due livelli, dichiarato.
- **Le larghezze delle zone** restano le nostre (dai raggi di §10.3), non
  quelle del riferimento (18/8/8/15/15/15).
- **`--rust` su `critical`**: la strada c'è, nessuna esecuzione l'ha percorsa.
- **Il margine del marchio** resta 0,04 sopra il minimo. Invariato, e invariata
  la decisione aperta di §25.13.
- **Due test della suite sono fragili** — `TestIconeVere::test_1` e `test_2`
  passano 11/11 isolati e falliscono a intermittenza in suite intera, perché
  cinque file di test usano il socket del core **vivo**. Non è di questo
  lavoro; è aperto a parte.
