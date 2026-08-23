# Cancello di governance — anche il riempimento sale

> **Zero codice.** Secondo cancello sulla stessa sezione, lo stesso giorno del
> primo (`docs/acceptance/CANCELLO-25.5.md`). Non è un ripensamento: è che il
> primo aveva alzato **il tratto** e lasciato **il riempimento** al tetto
> vecchio, e la differenza si è vista solo misurando il risultato.
>
> Decisione del proprietario, 23 agosto 2026: *«alza anche il riempimento»*.

---

## Che cosa la motiva

Dopo il primo emendamento il nucleo ha corpo continuo, fasce adiacenti e cerchi
concentrici. Resta una differenza, ed è **l'alternanza**:

| frazione del raggio | riferimento | noi |
|---|---|---|
| 0,33–0,47 | 38,9 | 36,7 |
| 0,48–0,54 | **132,7** | 52,3 |
| 0,55–0,61 | 84,1 | 50,5 |
| 0,62–0,73 | **107,2** | 50,8 |
| 0,74–0,86 | 45,4 | 52,0 |
| 0,87–0,98 | **92,8** | 51,7 |

Il riferimento oscilla fra 39 e 133; **noi stiamo fra 50 e 52, piatti.**

La causa è la riga «Riempimento del nucleo», fissata dal primo cancello a
L ≤ 48. Le bande chiare del riferimento sono **superfici** piene, non contorni
chiari su fondi scuri: una superficie a L 105 sfonda quella riga. È lo stesso
ceiling di prima, spostato di una riga — e finché resta lì, l'alternanza è
irriproducibile **per costruzione**, non per come la si costruisce.

---

## Che cosa cambia, e che cosa NON cambia

| Elemento | Prima | Dopo |
|---|---|---|
| **Riempimento** del nucleo | L ≤ 48 (`--cy-900`) | **`--cy-700`, L 100** |
| **Tacche su una fascia riempita sopra L 48** | *non nominate* | **`--cy-900`** — si invertono (riga nuova) |
| Tratto, riposo | `--cy-700` | **`--cy-700`** |
| Anello attivo | `--cy-500`, uno per volta | **`--cy-500`, uno per volta** |
| `--cy-100` | vietato | **vietato** |
| Testo del pannello | L 224 | **L 224** |
| Nessun filter, drop-shadow, bloom | invariante 19 | **invariante 19** |

### La riga nuova sulle tacche — e la sua correzione, lo stesso giorno

**Su una fascia riempita sopra L 48 il dettaglio si inverte: le tacche vanno a
`--cy-900`.** Una tacca si legge per **contrasto** contro il proprio fondo, e
su un fondo chiaro va scura.

> ### ⚠️ Come l'avevo scritta la prima volta, e perché era sbagliata
>
> La prima stesura di questa riga diceva **«nessuna»**. Veniva da un ritaglio a
> 9× del riferimento che mostrava il **corpo** delle fasce chiare liscio — vero,
> ma parziale. Un secondo ritaglio, in un altro punto del disco, mostra il
> dettaglio al loro **bordo interno**, che è esattamente dove `ReactorRing`
> disegna le proprie tacche.
>
> Reso senza tacche e guardato, il nucleo perdeva il dettaglio su **tre fasce
> su cinque** e leggeva come un disco pieno. Con le tacche invertite legge come
> uno strumento. La regola è corretta prima di indurirsi, e la prima stesura
> resta scritta qui perché il difetto era il metodo — **una sola inquadratura**
> — non il numero.

La riga esiste comunque, in una forma o nell'altra, perché senza di lei il
difetto tornerebbe peggiore: con fill e stroke entrambi a `--cy-700` le tacche
spariscono **da sole**, e riapparirebbero come fantasmi il giorno che qualcuno
cambia uno dei due valori senza sapere perché l'altro era lì.

---

## Quali fasce salgono — è una misura, non una composizione

Allineando ogni nostra fascia al profilo del riferimento nella stessa posizione
radiale:

| anello | la nostra fascia | il riferimento lì misura | |
|---|---|---|---|
| 0 (46 s) | 0,900–1,000 | **91,7** | chiara |
| 1 (74 s) | 0,800–0,883 | 46,8 | scura |
| 2 (120 s) | 0,633–0,783 | **87,4** | chiara |
| 3 (233 s) | 0,500–0,617 | **111,9** | chiara |
| 4 (ghiera) | 0,458–0,483 | 52,1 | scura |

**Tre chiare, due scure**, e non è una scelta: è dove cadono.

---

## Che cosa permette, e che cosa costa

**Permette** l'alternanza del riferimento: superfici chiare a L 100 fra
superfici scure a L 48, col dettaglio fine sulle seconde.

Restano fuori due cose, e nessuna delle due dipende da questa riga:

- i **picchi a L 243–254** del riferimento, che sono **bloom** — l'invariante 19
  li vieta indipendentemente da §25.5;
- la sua zona **«media» a L 84**: fra `--cy-900` e `--cy-700` la rampa fredda
  non ha gradini. `--cy-800` e `--cy-600` sono P1/P2 di `DIVARIO-PREMIUM.md` e
  non sono mai stati scritti. Due livelli, e va detto invece che approssimato.

**Costa** tre cose, da verificare misurando:

1. **Il marchio.** Il primo cancello l'aveva rotto, e la riparazione — legare
   la larghezza del nome al raggio del campo — dovrebbe reggere anche qui:
   `rCampo` è il bordo interno dell'anello 4, che **resta scuro**. Atteso
   invariato a **3,04:1**. Se cambia, il legame fra marchio e campo non è
   quello che si crede, ed è più importante del riempimento.
2. **La densità.** Tre fasce chiare valgono circa il **53 % dell'area del
   disco**: ~3,7 % del pavimento portato sopra L 60, da `L>60` 10,1 % a ~13,8 %.
   È il guadagno più grande che questo nucleo abbia mai prodotto — e se non
   arriva, la stima è sbagliata e va capito perché prima di andare avanti.
3. **Il precedente, di nuovo.** È il **secondo** emendamento alla stessa
   sezione nello stesso giorno. Una regola che si alza due volte in un giorno
   non è più un tetto: è una preferenza. Il presidio è che ogni passaggio abbia
   il proprio cancello scritto, la propria misura e il proprio test — e che
   ciò che tiene il vincolo non si sia mai mosso: `--cy-100` vietato, testo dei
   pannelli a L 224, un solo anello attivo.

---

## Costo del ritorno

Due valori in `ui/src/desk/sfondo.js` — il riempimento delle fasce chiare e la
regola sulle tacche — più un campo `chiara` nella tabella `ANELLI`, la riga di
§25.5 e un'asserzione in `tests/test_nucleo.py`.

Il pannello di §10.3 **non** è toccato: non chiede il corpo, non ha regole su
`data-chiara`, e i propri colori li dichiara per conto proprio.
